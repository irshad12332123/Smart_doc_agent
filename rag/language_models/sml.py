from transformers import pipeline, AutoTokenizer
from transformers.pipelines.text_generation import TextGenerationPipeline

def load_slm(model_name: str="meta-llama/Llama-3.2-1B-Instruct") -> TextGenerationPipeline:
    """
    Returns:
        TextGenerationPipeline:
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    pipe = pipeline("text-generation", model_name, tokenizer=tokenizer)

    return pipe
