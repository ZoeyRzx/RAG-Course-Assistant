from __future__ import annotations

from typing import Any

from .config import Settings
from .models import ChunkHit


SYSTEM_PROMPT = """
You are a question-answering assistant for course materials.
Use only the provided context.
If the context is insufficient, reply exactly:
I don't know based on the provided materials.
Every supported factual claim must cite one or more evidence blocks using [1], [2], etc.
Do not invent citations, page numbers, or facts that are not grounded in the context.
Keep the answer concise and directly responsive to the question.
""".strip()


def _resolve_torch_dtype(dtype_name: str) -> Any:
    if dtype_name == "auto":
        return "auto"

    import torch

    mapping = {
        "float16": torch.float16,
        "fp16": torch.float16,
        "float32": torch.float32,
        "fp32": torch.float32,
        "bfloat16": torch.bfloat16,
        "bf16": torch.bfloat16,
    }
    if dtype_name not in mapping:
        raise ValueError(f"Unsupported local generator dtype: {dtype_name}")
    return mapping[dtype_name]


class LocalCausalLMGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._tokenizer: Any | None = None
        self._model: Any | None = None

    def _load(self) -> tuple[Any, Any]:
        if self._tokenizer is not None and self._model is not None:
            return self._tokenizer, self._model

        from transformers import AutoModelForCausalLM, AutoTokenizer

        model_id = self.settings.local_generator_model
        trust_remote_code = self.settings.local_generator_trust_remote_code
        torch_dtype = _resolve_torch_dtype(self.settings.local_generator_dtype)

        import os
        if not os.path.exists(model_id):
            try:
                from modelscope import snapshot_download
                cache_dir = os.getenv("MODELSCOPE_CACHE_DIR")
                kwargs = {"cache_dir": cache_dir} if cache_dir else {}
                model_id = snapshot_download(model_id, **kwargs)
            except Exception:
                pass

        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=trust_remote_code,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            trust_remote_code=trust_remote_code,
        )
        model.eval()

        device = self.settings.local_generator_device
        if device:
            model = model.to(device)

        if tokenizer.pad_token is None and tokenizer.eos_token is not None:
            tokenizer.pad_token = tokenizer.eos_token

        self._tokenizer = tokenizer
        self._model = model
        return tokenizer, model

    def generate(self, question: str, context: str) -> str:
        import torch

        tokenizer, model = self._load()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Context:\n{context}\n\n"
                    f"Answer:"
                ),
            },
        ]

        prompt_text = self._format_prompt(tokenizer, messages)
        inputs = tokenizer(prompt_text, return_tensors="pt")
        model_device = next(model.parameters()).device
        inputs = {key: value.to(model_device) for key, value in inputs.items()}

        generation_kwargs = {
            "max_new_tokens": self.settings.local_generator_max_new_tokens,
            "do_sample": self.settings.local_generator_do_sample,
            "pad_token_id": (
                tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
            ),
            "eos_token_id": tokenizer.eos_token_id,
        }
        if self.settings.local_generator_do_sample:
            generation_kwargs["temperature"] = self.settings.local_generator_temperature

        with torch.inference_mode():
            output_ids = model.generate(**inputs, **generation_kwargs)

        generated_ids = output_ids[:, inputs["input_ids"].shape[1] :]
        text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
        return text

    def _format_prompt(self, tokenizer: Any, messages: list[dict[str, str]]) -> str:
        if hasattr(tokenizer, "apply_chat_template"):
            try:
                return tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=not self.settings.local_generator_disable_thinking,
                )
            except TypeError:
                return tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                )

        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"Question:\n{messages[-1]['content']}\n"
        )


class AnswerGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm: Any | None = None
        self._local_generator: LocalCausalLMGenerator | None = None

    def _get_llm(self) -> Any:
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(model=self.settings.generator_model, temperature=0)
        return self._llm

    def _get_local_generator(self) -> LocalCausalLMGenerator:
        if self._local_generator is None:
            self._local_generator = LocalCausalLMGenerator(self.settings)
        return self._local_generator

    def answer(self, question: str, supporting_chunks: list[ChunkHit]) -> str:
        if not supporting_chunks:
            return "I don't know based on the provided materials."

        context = self._build_context(supporting_chunks)
        prompt = f"""
{SYSTEM_PROMPT}

Question:
{question}

Context:
{context}

Answer:
""".strip()
        if self.settings.generator_backend == "openai":
            response = self._get_llm().invoke(prompt)
            return response.content.strip()
        if self.settings.generator_backend == "local":
            return self._get_local_generator().generate(question=question, context=context)
        raise ValueError(f"Unsupported generator backend: {self.settings.generator_backend}")

    def direct_answer(self, question: str) -> str:
        prompt = f"""
You are a helpful assistant.
Answer the following question as accurately as possible.
Do not use retrieved context.
This is a closed-book answer.

Question:
{question}

Answer:
""".strip()

        if self.settings.generator_backend == "openai":
            response = self._get_llm().invoke(prompt)
            return response.content.strip()

        if self.settings.generator_backend == "local":
            return self._get_local_generator().generate(question=question, context="")

        raise ValueError(f"Unsupported generator backend: {self.settings.generator_backend}")

    
    def _build_context(self, chunks: list[ChunkHit]) -> str:
        blocks: list[str] = []
        current_chars = 0

        for chunk in chunks:
            if chunk.page_start is not None and chunk.page_end not in (None, chunk.page_start):
                page_label = f"pp.{chunk.page_start}-{chunk.page_end}"
            elif chunk.page_start is not None:
                page_label = f"p.{chunk.page_start}"
            else:
                page_label = "page n/a"

            section_label = chunk.section or "section n/a"
            block = (
                f"[{chunk.source_id}] {chunk.title} | {page_label} | {section_label} | chunk_id={chunk.chunk_id}\n"
                f"{chunk.text}"
            )
            if current_chars + len(block) > self.settings.max_context_chars:
                break
            blocks.append(block)
            current_chars += len(block)

        return "\n\n".join(blocks)
