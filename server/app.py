from flask import Flask, request, Response
from flask_cors import CORS
import json
import re
import chromadb
import logging
from helper import cosine_similarity, ask_symptom_stream, suggest_treatment_stream, embedText, enrichUserInput  # Import from helper.py

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Initialize components
chroma_client = chromadb.PersistentClient(path="./medical_db")
symptoms_collection = chroma_client.get_collection("symptoms")


def process_patient_input(state):
    """State-aware processing generator"""
    try:
        # Initialize state
        state = state or {}
        initial_prompt = state.get('initial_prompt', '')
        asked_symptoms = set(state.get('asked_symptoms', []))
        excluded_candidates = state.get('excluded_candidates', [])
        depth = state.get('depth', 0)
        max_depth = 5
        confidence_threshold = state.get('confidence_threshold')
        if depth >= max_depth:
            yield json.dumps({
                'token': "Please consult a healthcare professional.",
                'complete': True
            }) + '\n'
            return

        if not initial_prompt:
            yield json.dumps({'token': "Describe your symptoms: "}) + '\n'
            return

        # Embed and query
        patient_symptoms = [s.strip() for s in re.split(';|,|and', initial_prompt) if s.strip()]
        patient_embeddings = embedText(patient_symptoms) if patient_symptoms else []
        input_embedding = embedText([initial_prompt])[0]
        
        results = symptoms_collection.query(
            query_embeddings=[input_embedding],
            n_results=3,
            include=["metadatas", "distances"],
            where={"disease": {"$nin": excluded_candidates}} if excluded_candidates else None
        )

        # Process candidates
        for candidate in zip(results['distances'][0], results['metadatas'][0], results['ids'][0]):
            distance, metadata, candidate_id = candidate
            current_confidence = 1 - distance
            print(current_confidence, confidence_threshold, current_confidence >= confidence_threshold)


            # If confidence threshold is met, stream diagnosis and treatment
            if current_confidence >= confidence_threshold:
                yield json.dumps({
                    'token': f"Based on your symptoms, I believe you may have {metadata['disease']}. ",
                    'state': {
                        'diagnosis': metadata['disease'],
                        'confidence': current_confidence,
                        'complete': False
                    }
                }) + '\n'

                # Stream treatment explanation
                treatment_prompt = (
                    f"Explain this treatment in simple terms: {metadata['treament']} "
                    f"Context: Patient showed symptoms matching {metadata['disease']}"
                )
                yield from suggest_treatment_stream(prompt=treatment_prompt, max_tokens=150)

                # Final state update
                yield json.dumps({
                    'state': {
                        'diagnosis': metadata['disease'],
                        'confidence': current_confidence,
                        'complete': True
                    }
                }) + '\n'
                return

            # If confidence is not met, ask follow-up questions
            stored_symptoms = [s.strip() for s in metadata['symptom'].split(',')]
            stored_embeddings = embedText(stored_symptoms)

            new_symptoms = [
                symptom for symptom, emb in zip(stored_symptoms, stored_embeddings)
                if max([cosine_similarity(emb, pe) for pe in patient_embeddings] + [0]) < 0.7
                and symptom not in asked_symptoms
            ]

            if not new_symptoms:
                excluded_candidates.append(metadata['disease'])
                continue

            for symptom in new_symptoms:
                asked_symptoms.add(symptom)
                question = (
                    f"are you experiencing {symptom} "
                )
                print(symptom)
                yield from ask_symptom_stream(question, max_tokens=150)
                yield json.dumps({
                    'token': "",
                    'state': {
                        'initial_prompt': initial_prompt,
                        'asked_symptoms': list(asked_symptoms),
                        'excluded_candidates': excluded_candidates,
                        'confidence_threshold':confidence_threshold,
                        'depth': depth + 1,
                        'complete': False
                    }
                }) + '\n'
                return

        # If no candidates match
        yield json.dumps({
            'message': "Unable to determine diagnosis. Please consult a doctor.",
            'complete': True
        }) + '\n'

    except Exception as e:
        logging.error(f"Error in processing: {str(e)}")
        yield json.dumps({
            'error': "An error occurred. Please try again.",
            'complete': True
        }) + '\n'


@app.route('/chat', methods=['POST'])
def chat_handler():
    data = request.json
    user_input = data.get('message', '')
    client_state = data.get('state', {})


    def generate():
        processed_client_state = enrichUserInput(user_input,client_state)
        print(processed_client_state)

        for response in process_patient_input(processed_client_state):
            yield f"data: {response}\n\n"

    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
