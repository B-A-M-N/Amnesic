from setuptools import setup, find_packages

setup(
    name="amnesic",
    version="0.1.0",
    description="A persistent memory and governance layer for local LLMs.",
    author="BAMN",
    packages=find_packages(),
    install_requires=[
        "langgraph",
        "langchain-ollama",
        "langchain-community",
        "fastembed",
        "numpy",
        "rich"
    ],
    python_requires=">=3.10",
)
