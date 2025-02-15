
import json
import chromadb
from nomic import embed
from gpt4all import GPT4All

# Replace below path with the path where you want to install your model
model_path = r"E:\Personal Projects\LLM Prac\Models"



def seedDatabase():
    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(path="./medical_db")

    # Create or get the collection
    symptoms_collection = chroma_client.get_or_create_collection(name="symptoms")

    # Load the JSON file containing symptoms
    with open("symptoms_data.json", "r", encoding="utf-8") as file:
        symptoms = json.load(file)

    # Generate and store symptom embeddings
    for symptom in symptoms:
        # Construct text representation for embedding
        symptom_text = f"{symptom['symptom']} - {symptom['related_diseases']}"

        # Generate embedding
        embedding = embed.text([symptom_text], inference_mode="local")['embeddings'][0]

        print("Saving: ", symptom['id'])
        # Add to ChromaDB
        symptoms_collection.add(
            ids=[symptom['id']],
            embeddings=[embedding],
            metadatas=[
                {
                    "symptom": symptom['symptom'],
                    "disease": symptom['related_diseases'],
                    "treament":symptom['treatment']
                }
            ]
        )

    print("Symptoms successfully stored in ChromaDB.", symptoms_collection.count())

def installLLM():
    llm = GPT4All("Phi-3-mini-4k-instruct.Q4_0.gguf", model_path=model_path)

seedDatabase()
installLLM()