#!/bin/bash

echo "Starting Ollama Server..."
ollama serve & # Start Ollama in the background

echo "Ollama is ready, creating the model..."

ollama create gemma_model -f llm/Modelfile
ollama run gemma_model 