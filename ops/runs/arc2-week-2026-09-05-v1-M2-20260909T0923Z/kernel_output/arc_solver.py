from unsloth import FastLanguageModel, UnslothTrainingArguments, UnslothTrainer
from arc_loader import ArcDataset, QwenFormatter

import gc
import os
import io
import time
import torch
import numpy as np
from tqdm import tqdm
from datasets import Dataset
from collections import defaultdict

from typing import Any, Union
from transformers import DataCollatorForLanguageModeling

import logging
from contextlib import redirect_stdout, redirect_stderr

from peft import get_peft_model_state_dict, set_peft_model_state_dict
from pathlib import Path

import bz2
import pickle
import sys
import json

logging.disable(logging.WARNING)

ADAPTER_WEIGHT_NAMES = (
    "adapter_ttt.safetensors",
    "adapter_model.safetensors",
    "adapter_model.bin",
)


def resolve_adapter_path():
    env = os.environ.get("ARC2_ADAPTER_PATH", "").strip()
    roots = []
    if env:
        roots.append(Path(env))
    roots.extend(
        [
            Path("/kaggle/input/arc2-m2-sft-adapter-v1"),
            Path("/kaggle/input/arc2-m2-sft-adapter-v1/adapter"),
            Path("/kaggle/input/arc2-m1-sft-adapter-v1"),
            Path("/kaggle/input/arc2-m1-sft-adapter-v1/adapter"),
        ]
    )
    kaggle_input = Path("/kaggle/input")
    if kaggle_input.is_dir():
        for name in ADAPTER_WEIGHT_NAMES:
            for path in sorted(kaggle_input.rglob(name)):
                roots.append(path.parent)
    seen = set()
    for root in roots:
        key = str(root)
        if not key or key in seen:
            continue
        seen.add(key)
        if any((root / name).exists() for name in ADAPTER_WEIGHT_NAMES):
            return root
    return None


def _candidate_key_names(key: str) -> list[str]:
    names = [key]
    for prefix in ("base_model.model.", "base_model.", "model."):
        if key.startswith(prefix):
            names.append(key[len(prefix) :])
        else:
            names.append(prefix + key)
    return names


def align_adapter_state(loaded: dict, target_keys) -> dict:
    target = set(target_keys)
    aligned = {}
    used = set()
    for key, value in loaded.items():
        if key in target and key not in used:
            aligned[key] = value
            used.add(key)
            continue
        for candidate in _candidate_key_names(key):
            if candidate in target and candidate not in used:
                aligned[candidate] = value
                used.add(candidate)
                break
    return aligned


def _write_adapter_receipt(payload: dict) -> None:
    text = json.dumps(payload, indent=2) + "\n"
    destinations = [Path("adapter_load.json")]
    working = Path("/kaggle/working")
    if working.is_dir():
        destinations.append(working / "adapter_load.json")
    output_dir = os.environ.get("ARC2_OUTPUT_DIR")
    if output_dir:
        destinations.append(Path(output_dir).parent / "adapter_load.json")
    for path in destinations:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except OSError:
            continue


def load_optional_sft_adapter(model, default_weights):
    """Replace random LoRA with a train-only adapter when a path is present."""
    root = resolve_adapter_path()
    payload = {
        "found": root is not None,
        "root": str(root) if root is not None else None,
        "kaggle_input": sorted(str(p) for p in Path("/kaggle/input").iterdir()) if Path("/kaggle/input").is_dir() else [],
    }
    if root is None:
        message = "[adapter] not found; using random LoRA init"
        print(message, flush=True)
        print(message, file=sys.stderr, flush=True)
        _write_adapter_receipt(payload)
        return default_weights
    weight_path = None
    for name in ADAPTER_WEIGHT_NAMES:
        candidate = root / name
        if candidate.exists():
            weight_path = candidate
            break
    if weight_path is None:
        payload["error"] = "no weight file"
        _write_adapter_receipt(payload)
        return default_weights
    if weight_path.suffix == ".safetensors":
        from safetensors.torch import load_file

        loaded = load_file(str(weight_path), device="cpu")
    else:
        loaded = torch.load(str(weight_path), map_location="cpu")
    target_keys = list(default_weights.keys())
    aligned = align_adapter_state(loaded, target_keys)
    payload.update(
        {
            "weight_file": str(weight_path),
            "n_loaded": len(loaded),
            "n_target": len(target_keys),
            "n_aligned": len(aligned),
            "loaded_head": list(loaded.keys())[:8],
            "target_head": target_keys[:8],
        }
    )
    if not aligned:
        payload["error"] = "zero overlapping keys"
        message = f"[adapter] key mismatch file={weight_path} loaded={len(loaded)} target={len(target_keys)}"
        print(message, flush=True)
        print(message, file=sys.stderr, flush=True)
        _write_adapter_receipt(payload)
        return default_weights
    set_peft_model_state_dict(model, aligned, adapter_name="default")
    refreshed = get_peft_model_state_dict(model, adapter_name="default")
    payload["n_refreshed"] = len(refreshed)
    message = (
        f"[adapter] loaded {weight_path} aligned={len(aligned)}/{len(target_keys)} "
        f"refreshed={len(refreshed)}"
    )
    print(message, flush=True)
    print(message, file=sys.stderr, flush=True)
    _write_adapter_receipt(payload)
    return {k: v.clone().detach() for k, v in refreshed.items()}


def stable_seed_for_key(key, offset=0):
    base = sum((i + 1) * ord(ch) for i, ch in enumerate(str(key)))
    return (base + int(offset)) % (1024 ** 2)


ARC_VOCAB = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "Ċ": 10,
    "<|im_end|>": 15,
}

ARC_TOKENS = list(ARC_VOCAB.values())
USER_TOKEN_ID = 11
ASSISTANT_TOKEN_ID = 12
PAD_ID = 13
EOS_ID = 15


class UnslothFixedTrainer(UnslothTrainer):

    # Issue https://github.com/unslothai/unsloth/issues/2435

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        """Fixed compute_loss that handles Unsloth's view tensor issue"""
        if self.label_smoother is not None and "labels" in inputs:
            labels = inputs.pop("labels")
        else:
            labels = None
        outputs = model(**inputs)
        if labels is not None:
            unwrapped_model = self.accelerator.unwrap_model(model)
            if hasattr(unwrapped_model, "_get_name") and "unsloth" in unwrapped_model._get_name().lower():
                loss = self.label_smoother(outputs, labels, shift_labels=True)
            else:
                loss = self.label_smoother(outputs, labels)
        else:
            loss = outputs["loss"] if isinstance(outputs, dict) else outputs[0]
        if hasattr(loss, "clone"):
            loss = loss.clone()
        # Now safe for DDP gradient scaling
        if self.accelerator.num_processes > 1:
            loss = loss * self.accelerator.num_processes
        return (loss, outputs) if return_outputs else loss


class QwenDataCollatorForCompletionOnlyLM(DataCollatorForLanguageModeling):

    def torch_call(self, examples: list[Union[list[int], Any, dict[str, Any]]]) -> dict[str, Any]:
        batch = super().torch_call(examples)
        for i in range(len(examples)):
            labels = batch["input_ids"][i].clone()
            user_start_idx = np.where(labels == USER_TOKEN_ID)[0].tolist()
            assistant_start_idx = np.where(labels == ASSISTANT_TOKEN_ID)[0].tolist()
            start_idx = sorted(user_start_idx + assistant_start_idx)
            end_idx = np.where(labels == EOS_ID)[0]
            batch["labels"][i, :] = -100
            for j, (start, end) in enumerate(zip(start_idx, end_idx)):
                assert start < end
                if j % 2 == 1:
                    start += 2
                    end += 1
                    batch["labels"][i, start:end] = labels[start:end]
        return batch


# Minimal performance patch: preserve the baseline beam set and ranking, but transfer
# only the 12 ARC-token NLL values to CPU instead of every Qwen vocabulary logit.
_ARC_TOKEN_ID_CACHE = {}


def _arc_token_ids(device):
    key = str(device)
    token_ids = _ARC_TOKEN_ID_CACHE.get(key)
    if token_ids is None:
        token_ids = torch.tensor(ARC_TOKENS, dtype=torch.long, device=device)
        _ARC_TOKEN_ID_CACHE[key] = token_ids
    return token_ids


def turbo_dfs(model, logits, max_new_tokens, max_score, scores, pos, cache, start_time, end_time) -> dict:

    n = logits.size(0)

    # Algebraically identical to: scores - logits.float().cpu().log_softmax(-1),
    # restricted to the same ARC_TOKENS used by the baseline DFS loop.
    logits_f = logits.float()
    token_ids = _arc_token_ids(logits.device)
    arc_logits = logits_f.index_select(-1, token_ids)
    nll = (
        torch.as_tensor(scores, dtype=torch.float32, device=logits.device).view(n, 1)
        + torch.logsumexp(logits_f, dim=-1, keepdim=True)
        - arc_logits
    ).cpu()

    suffixes = defaultdict(list)

    candidates = dict()

    for i in range(n):
        candidates[i] = []
        for token_idx, t in enumerate(ARC_TOKENS):
            score = nll[i, token_idx].item()
            if score < max_score:
                if t == EOS_ID:
                    suffixes[i].append((score, [t]))
                elif max_new_tokens > 1:
                    candidates[i].append((score, t))

    for i in range(n):
        candidates[i] = sorted(candidates[i], key=lambda x:x[0]) #[:5]
    
    while time.time() - start_time < 540 and time.time() < end_time:

        batch_tokens = []
        batch_scores = []
        num_alive_beams = 0

        for i in range(n):
            if len(candidates[i]) == 0:
                batch_tokens.append(PAD_ID)
                batch_scores.append(1000)
            else:
                score, t = candidates[i].pop(0)
                batch_tokens.append(t)
                batch_scores.append(score)
                num_alive_beams += 1

        if num_alive_beams == 0:
            break

        outputs = model(
            input_ids=torch.tensor(batch_tokens, device=model.device, dtype=torch.long).view(-1, 1),
            position_ids=torch.full((n, 1), pos, device=model.device),
            past_key_values=cache,
            return_dict=True,
            use_cache=True,
        )

        next_suffixes = turbo_dfs(
            model,
            logits=outputs.logits[:, -1],
            max_new_tokens=max_new_tokens-1,
            max_score=max_score,
            scores=batch_scores,
            pos=pos+1,
            cache=outputs.past_key_values,
            start_time=start_time,
            end_time=end_time,
        )

        for batch_id, beams in next_suffixes.items():
            for score, suffix_tokens in beams:
                suffix_tokens.insert(0, batch_tokens[batch_id])
                suffixes[batch_id].append((score, suffix_tokens))

    return suffixes


@torch.no_grad()
def inference_turbo_dfs(model, prefix_tokens, max_new_tokens, max_score, end_time):
    input_ids = torch.tensor(prefix_tokens, device=model.device, dtype=torch.long)
    outputs = model(input_ids=input_ids, return_dict=True, use_cache=True)
    suffixes = turbo_dfs(
        model,
        logits=outputs.logits[:, -1],
        max_new_tokens=max_new_tokens,
        max_score=max_score,
        scores=[0.0] * input_ids.size(0),
        pos=input_ids.size(1),
        cache=outputs.past_key_values,
        start_time=time.time(),
        end_time=end_time,
    )
    result = []
    for batch_id, beams in suffixes.items():
        sorted_beams = sorted(beams, key=lambda x:x[0])
        result.append((batch_id, sorted_beams))
    return result


@torch.no_grad()
def calc_scores(queries, answers, tokenizer, model):
    batch_query_tokens = []
    batch_answer_tokens = []
    batch_tokens = []
    batch_lengths = []
    for query, answer in zip(queries, answers):
        query_tokens = tokenizer.encode(query)
        answer_tokens = tokenizer.encode(answer)
        tokens = query_tokens + answer_tokens
        batch_query_tokens.append(query_tokens)
        batch_answer_tokens.append(answer_tokens)
        batch_tokens.append(tokens)
        batch_lengths.append(len(tokens))
    max_len = max(batch_lengths)
    padded_tokens = []
    for tokens in batch_tokens:
        padded = tokens + [PAD_ID] * (max_len - len(tokens))
        padded_tokens.append(padded)
    input_ids = torch.tensor(padded_tokens, device=model.device, dtype=torch.long)

    # Keep logits on GPU and gather only the target-token scores. KV cache is not
    # consumed by teacher-forced scoring, so disabling it removes redundant writes.
    outputs = model(input_ids=input_ids, return_dict=True, use_cache=False)
    batch_logits = outputs.logits.float()
    batch_log_norm = torch.logsumexp(batch_logits, dim=-1)
    result = []
    for row_id, (query_tokens, answer_tokens) in enumerate(zip(batch_query_tokens, batch_answer_tokens)):
        query_length = len(query_tokens)
        answer_length = len(answer_tokens)
        positions = torch.arange(
            query_length - 1,
            query_length - 1 + answer_length,
            device=model.device,
        )
        target_tokens = torch.tensor(answer_tokens, device=model.device, dtype=torch.long)
        answer_log_probs = (
            batch_logits[row_id, positions, target_tokens]
            - batch_log_norm[row_id, positions]
        )
        result.append(-answer_log_probs.sum().item())
    return result


def worker(rank, queue, end_time):

    rerun_mode = os.getenv("KAGGLE_IS_COMPETITION_RERUN")

    peft_params = dict(
        r=256,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj", "embed_tokens", "lm_head"],
        lora_alpha=32,
        lora_dropout=0.0,
        bias="none",
        use_gradient_checkpointing=False,
        random_state=42,
        use_rslora=True,
        loftq_config=None,
    )

    train_args = dict(
        per_device_eval_batch_size=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        num_train_epochs=1,
        warmup_steps=0,
        warmup_ratio=0.1,
        max_grad_norm=1.0,
        learning_rate=5e-5,
        optim="adamw_torch",
        weight_decay=0.0,
        lr_scheduler_type="cosine",
        seed=42,
        report_to="none",
        save_strategy="no",
        eval_strategy="no",
        logging_strategy="no",
        fp16=False,
        bf16=True,
        # Disable FSDP (use standard DDP)
        fsdp="",
        ddp_find_unused_parameters=False,
        dataloader_num_workers=0,
        gradient_checkpointing=False,
    )

    max_seq_length = 8192

    model_name = os.environ.get(
        "ARC2_MODEL_PATH",
        "/kaggle/input/models/sorokin/qwen3_4b_grids15_sft139/transformers/bfloat16/1",
    )
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        full_finetuning=False,
        load_in_4bit=False,
        local_files_only=True,
        use_gradient_checkpointing=False,
        max_seq_length=max_seq_length,
    )

    model = FastLanguageModel.get_peft_model(model, **peft_params)

    for name, param in model.named_parameters():
        if param.dtype == torch.float32:
            param.data = param.data.to(torch.bfloat16)

    default_weights = get_peft_model_state_dict(model, adapter_name="default")
    default_weights = {k: v.clone().detach() for k, v in default_weights.items()}
    default_weights = load_optional_sft_adapter(model, default_weights)

    collator = QwenDataCollatorForCompletionOnlyLM(
        tokenizer=tokenizer,
        mlm=False,
    )

    formatter = QwenFormatter(tokenizer=tokenizer)

    max_new_tokens = formatter.max_new_tokens()

    max_score = -np.log(0.2)

    test_path = os.environ.get("ARC2_INPUT_PATH")
    if not test_path:
        if rerun_mode:
            test_path = "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_test_challenges.json"
        else:
            test_path = "/kaggle/input/competitions/arc-prize-2026-arc-agi-2/arc-agi_evaluation_challenges.json"

    arc_test_set = ArcDataset.from_file(test_path)

    dir_outputs = os.environ.get("ARC2_OUTPUT_DIR", "/kaggle/inference_outputs")
    os.makedirs(dir_outputs, exist_ok=True)

    while not queue.empty():

        if time.time() > end_time:
            print(f"[Rank {rank}] stop!")
            break

        key = queue.get()
        if key is None:
            break
        
        start_time = time.time()
        
        torch.cuda.reset_peak_memory_stats()

        load_result = set_peft_model_state_dict(
            model,
            default_weights.copy(),
            adapter_name="default",
        )

        model = FastLanguageModel.for_training(model)

        puzzle_ds = arc_test_set.change_keys([key])

        train_ds = puzzle_ds.augment(n=16, shfl_keys=True, seed=1)
        train_ds = train_ds.cut_to_len(formatter=formatter, name="text", max_len=max_seq_length)

        with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
            
            trainer = UnslothFixedTrainer(
                model=model,
                tokenizer=tokenizer,
                data_collator=collator,
                train_dataset=Dataset.from_list(train_ds.as_list(formatter)),
                dataset_text_field="text",
                max_seq_length=max_seq_length,
                args=UnslothTrainingArguments(**train_args),
            )

            stats = trainer.train()

            model = trainer.accelerator.unwrap_model(model, keep_fp32_wrapper=False)

            del trainer

        model = FastLanguageModel.for_inference(model)
        
        gc.collect()
        torch.cuda.empty_cache()
            
        memory_allocated = torch.cuda.max_memory_allocated() // 1024**2
        print(f"[Rank {rank}] allocated {memory_allocated}MB for training")

        torch.cuda.reset_peak_memory_stats()
        
        print(f"[Rank {rank}] training stats for puzzle {key}: {stats}")

        puzzle_ds_multi = puzzle_ds.split_multi_replies()

        eval_ds = puzzle_ds_multi.augment(n=2, seed=2)
        eval_ds = eval_ds.cut_to_len(formatter=formatter, name="input", max_len=max_seq_length-max_new_tokens)

        test_id_to_subkeys = defaultdict(list)
        for subkey in sorted(eval_ds.keys):
            test_id = subkey.split(".")[0].split("_")[1]
            test_id_to_subkeys[test_id].append(subkey)

        batches = []
        for test_id, subkeys in test_id_to_subkeys.items():
            # 0: permute x 2
            # 4: rot90.rot90.permute x 2
            batch = []
            for offset in [0, 4]:
                batch.extend(subkeys[offset:offset+2])
            batches.append(batch)
            # 2: permute.rot90 x 2
            # 6: rot90.rot90.rot90.permute x 2
            batch = []
            for offset in [2, 6]:
                batch.extend(subkeys[offset:offset+2])
            batches.append(batch)
        for test_id, subkeys in test_id_to_subkeys.items():
            # 8: transpose.permute x 2
            # 12: transpose.rot90.rot90.permute x 2
            batch = []
            for offset in [8, 12]:
                batch.extend(subkeys[offset:offset+2])
            batches.append(batch)
            # 10: transpose.rot90.permute x 2
            # 14: transpose.rot90.rot90.rot90.permute x 2
            batch = []
            for offset in [10, 14]:
                batch.extend(subkeys[offset:offset+2])
            batches.append(batch)

        with torch.inference_mode():
                
            known_scores = {}

            for subkeys in batches:

                spend_time = time.time() - start_time
                if spend_time > 1200 or time.time() > end_time:
                    print(f"[Rank {rank}] timeout after {spend_time:.1f}s for puzzle {key}")
                    break

                print(f"[Rank {rank}] decoding {subkeys}")

                tokens = []
                for subkey in subkeys:
                    data = eval_ds.get(subkey, formatter)
                    tokens.append(tokenizer.encode(data["input"]))

                dfs_result = inference_turbo_dfs(model, tokens, max_new_tokens, max_score, end_time)

                for subkey_id, scored_beams in dfs_result:

                    subkey = subkeys[subkey_id]
                    bk = subkey.split(".")[0]
                    decoded_result = []

                    for beam_score, tokens in scored_beams:

                        array = formatter.convert_tokens_to_array(tokens)
                        if array is None:
                            continue

                        solution = puzzle_ds_multi.invert_mod(array, subkey, inv_perm=True)

                        grid_id = (bk, tuple(map(tuple, solution)))

                        if grid_id in known_scores:
                            augmented_scores = known_scores[grid_id]
                        else:
                            print(f"[Rank {rank}] scoring {subkey} #{len(decoded_result)}")
                            aug_dataset = ArcDataset(
                                keys=[bk],
                                queries={bk: puzzle_ds_multi.queries.get(bk)},
                                replies={bk: [solution.tolist()]},
                            )
                            aug_dataset = aug_dataset.augment(seed=stable_seed_for_key(bk, os.getenv('ARC_AUG_SEED_OFFSET', 0)))
                            aug_dataset = aug_dataset.cut_to_len(formatter=formatter, name="input", max_len=max_seq_length-max_new_tokens)
                            aug_queries = []
                            aug_answers = []
                            for augmented_sample in aug_dataset.as_list(formatter):
                                aug_queries.append(augmented_sample["input"])
                                aug_answers.append(augmented_sample["reply"])
                            augmented_scores1 = calc_scores(aug_queries[:4], aug_answers[:4], tokenizer, model)
                            augmented_scores2 = calc_scores(aug_queries[4:], aug_answers[4:], tokenizer, model)
                            augmented_scores = augmented_scores1 + augmented_scores2
                            known_scores[grid_id] = augmented_scores
                        
                        decoded_result.append({
                            "beam_score": beam_score,
                            "score_aug": augmented_scores,
                            "solution": solution,
                        })

                    if len(decoded_result):
                        with bz2.BZ2File(os.path.join(dir_outputs, subkey), "w") as f:
                            pickle.dump(decoded_result, f)

        memory_allocated = torch.cuda.max_memory_allocated() // 1024**2
        print(f"[Rank {rank}] allocated {memory_allocated}MB for inference")
        
        spend_time = time.time() - start_time
        print(f"[Rank {rank}] finished {key} in {spend_time:.1f}s")
