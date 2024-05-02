import streamlit as st
import numpy as np
import pretty_midi
import os
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical
import io
import fluidsynth
from scipy.io import wavfile
import subprocess
from pydub import AudioSegment
from midi2audio import FluidSynth
import mido
from scipy import signal
import tempfile
bg_image = "/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/piano.webp"

#st.image(bg_image, use_column_width=True)
st.image(bg_image, use_column_width=True, width="100%")
# # Check for GPU availability
# if tf.config.experimental.list_physical_devices('GPU'):
#     st.write("Using GPU")
# else:
#     st.write("Using CPU")

# Set the background image as the page background
st.markdown(
    f"""
    <style>
    .reportview-container {{
        background: url("{bg_image}");
        background-size: cover;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
    }}
    .title {{
        color: white;
        font-size: 3em;
        text-align: center;
    }}
    .intro {{
        color: white;
        font-size: 1.5em;
        text-align: center;
        margin-top: 20px;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# Display the title
st.markdown("<h1 class='title'>Classical Music Generation</h1>", unsafe_allow_html=True)
st.markdown("<p class='intro' style='font-size: 14px; text-align: justify;'>Welcome to our Classical Music Generation application! This project leverages Long Short-Term Memory (LSTM) neural networks with embedding layers to generate classical music sequences. Using MIDI files as input, the application extracts detailed note sequences, including pitch, velocity, start, and end times. These sequences are then used to train the LSTM model, which learns patterns in the music data. Once trained, the model can generate new music sequences based on a provided seed sequence. By adjusting parameters such as temperature, users can control the variability and creativity of the generated music. The generated music sequences are then converted to MIDI format to ensure all notes are audible. With this application, users can explore the fascinating world of classical music generation, creating unique compositions with just a click of a button!</p>", unsafe_allow_html=True)

@st.cache_resource
def load_midi_details(directory):
    """Load all MIDI files in the directory and extract detailed note sequences."""
    all_sequences = []
    for filename in os.listdir(directory):
        if filename.endswith('.mid'):
            path = os.path.join(directory, filename)
            midi_data = pretty_midi.PrettyMIDI(path)
            for instrument in midi_data.instruments:
                for note in instrument.notes:
                    all_sequences.append({
                        'pitch': note.pitch,
                        'velocity': note.velocity,
                        'start': note.start,
                        'end': note.end
                    })
    return all_sequences


def create_input_target_sequences(sequence, seq_length, vocab_size):
    """Create input and target sequences from detailed note sequences."""
    input_sequences = []
    target_sequences = []
    for i in range(len(sequence) - seq_length):
        input_seq = [[event['pitch']] for event in sequence[i:i + seq_length]]
        target_pitch = sequence[i + seq_length]['pitch']
        target_seq = to_categorical(target_pitch, num_classes=vocab_size)
        input_sequences.append(input_seq)
        target_sequences.append(target_seq)
    return np.array(input_sequences), np.array(target_sequences)


def load_existing_model(model_path):
    """Load an existing TensorFlow model from the given path."""
    return load_model(model_path)


def generate_music(model, seed_sequence, length=10, steps_per_second=5, temperature=2):
    """Generate music from a seed sequence aiming for a total duration using a temperature parameter."""
    generated_sequence = np.copy(seed_sequence)  # Copy to avoid modifying the original seed
    total_steps = length * steps_per_second  # Total steps needed for desired duration

    for _ in range(total_steps):
        # Predict the next step using the last 'seq_length' elements in the generated_sequence
        prediction = model.predict(np.expand_dims(generated_sequence[-seq_length:], axis=0))[0]

        # Apply temperature to the prediction probabilities and normalize
        prediction = np.log(prediction + 1e-8) / temperature  # Smoothing and apply temperature
        exp_prediction = np.exp(prediction)
        prediction = exp_prediction / np.sum(exp_prediction)

        # Sample an index from the probability array
        predicted_pitch = np.random.choice(len(prediction), p=prediction)

        # Append the predicted pitch to the generated sequence
        generated_sequence = np.vstack([generated_sequence, predicted_pitch])

    #st.write("Generated sequence with variability:", generated_sequence[-30:])
    return generated_sequence

def generated_to_midi(generated_sequence, fs=100, total_duration=6):
    """Convert generated sequence to MIDI file, ensuring all notes are audible."""
    pm = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=0)

    # Calculate the duration per step based on total duration and number of notes
    duration_per_step = total_duration / len(generated_sequence)
    min_duration = 0.1  # Set a minimum note duration for clarity

    # Initialize the current time to track the start time of each note
    current_time = 0

    for step in generated_sequence:
        pitch = int(np.clip(step[0], 21, 108))  # Scale and clip pitch values to MIDI range
        velocity = 100  # Fixed velocity for all notes

        # Set start and end time for each note
        start = current_time
        end = start + max(min_duration, duration_per_step)

        # Create a MIDI note with the determined pitch, velocity, start, and end times
        note = pretty_midi.Note(
            velocity=velocity,
            pitch=pitch,
            start=start,
            end=end
        )
        instrument.notes.append(note)

        # Update the current time to the end of this note for the next note
        current_time = end

    # Add the instrument to the PrettyMIDI object
    pm.instruments.append(instrument)
    print("The generated MIDI")
    return pm


def midi_to_wav(midi_path, wav_path):
    fs = FluidSynth()
    fs.midi_to_audio(midi_path, wav_path)

# Define the directory options and their corresponding model paths
composer_models = {
    'albeniz': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/albeniz.h5',
    'bach': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/bach.h5',
    'balakir': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/balakir.h5',
    'beeth':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/beeth.h5',
    'borodin':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/borodin.h5',
    'brahms':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/brahms.h5',
    'burgm':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/burgm.h5',
    'chopin':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/chopin.h5',
    'debussy':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/debussy.h5',
    'granados':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/granados.h5',
    'grieg':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/grieg.h5',
    'haydn':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/haydn.h5',
    'liszt':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/liszt.h5',
    'mendelssohn':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/mendelssohn.h5',
    'mozart':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/mozart.h5',
    'muss':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/muss.h5',
    'schubert':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/schubert.h5',
    'schumann':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/schumann.h5',
    'tschai':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/tschai.h5'

}

# Define the directory options for training and prediction MIDI files
training_midi_directory_options = {
    'albeniz': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/albeniz',
    'bach': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/bach',
    'balakir': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/balakir',
    'beeth':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/beeth',
    'borodin':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/borodin',
    'brahms':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/brahms',
    'burgm':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/burgm',
    'chopin':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/chopin',
    'debussy':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/debussy',
    'granados':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/granados',
    'grieg':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/grieg',
    'haydn':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/haydn',
    'liszt':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/liszt',
    'mendelssohn':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/mendelssohn',
    'mozart':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/mozart',
    'muss':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/muss',
    'schubert':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/schubert',
    'schumann':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/schumann',
    'tschai':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/tschai'
}

prediction_midi_directory_options = {
    'albeniz': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/albeniz',
    'bach': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/bach',
    'balakir': '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/balakir',
    'beeth':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/beeth',
    'borodin':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/borodin',
    'brahms':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/brahms',
    'burgm':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/burgm',
    'chopin':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/chopin',
    'debussy':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/debussy',
    'granados':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/granados',
    'grieg':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/grieg',
    'haydn':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/haydn',
    'liszt':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/liszt',
    'mendelssohn':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/mendelssohn',
    'mozart':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/mozart',
    'muss':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/muss',
    'schubert':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/schubert',
    'schumann':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/schumann',
    'tschai':'/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/archive/tschai'
}

#st.markdown('<div class="center"><h1>Classical Music Generation</h1></div>', unsafe_allow_html=True)

# Select composer for training
selected_composer_training = st.selectbox("Select composer for training:", list(composer_models.keys()))
training_directory_path = training_midi_directory_options[selected_composer_training]

# Parameters for the sequence creation
seq_length = 30  # Length of the input sequences
vocab_size = 128  # Number of unique pitches (for MIDI, typically 128)


if st.button('Load Data'):
    # Load training data
    training_sequences = load_midi_details(training_directory_path)
    training_input_sequences, training_target_sequences = create_input_target_sequences(training_sequences, seq_length,
                                                                                        vocab_size)
    #st.write(f"Loaded {len(training_sequences)} training sequences.")
    #st.write(f"Training input sequences shape: {training_input_sequences.shape}")
    #st.write(f"Training target sequences shape: {training_target_sequences.shape}")

    # Load the selected model for training
    model_path = composer_models[selected_composer_training]
    try:
        training_model = load_existing_model(model_path)
        st.success("Training model loaded successfully.")
    except Exception as e:
        st.error(f"Error loading training model: {e}")

# Select composer for prediction
selected_composer_prediction = st.selectbox("Select composer for prediction:", list(composer_models.keys()))
prediction_directory_path = prediction_midi_directory_options[selected_composer_prediction]

temperature = st.slider("Temperature", min_value=0.0, max_value=5.0, step=0.1)


# Generate music based on the loaded model
if st.button('Generate Music'):

    # Load prediction data
    prediction_sequences = load_midi_details(prediction_directory_path)
    prediction_input_sequences, prediction_target_sequences = create_input_target_sequences(prediction_sequences,
                                                                                            seq_length, vocab_size)
    #st.write(f"Loaded {len(prediction_sequences)} prediction sequences.")
    #st.write(f"Prediction input sequences shape: {prediction_input_sequences.shape}")
    #st.write(f"Prediction target sequences shape: {prediction_target_sequences.shape}")

    training_model = load_existing_model(composer_models[selected_composer_training])

    seed_index = 0
    seed_sequence = prediction_input_sequences[seed_index]
    # Generate music using the training model
    generated_music = generate_music(training_model, seed_sequence)

    # Convert generated sequence to MIDI
    generated_music_midi = generated_to_midi(generated_music,total_duration=15)
    #output_path = '/Users/dishakacha/Downloads/Deep_Learning/Deep_Learing/Project/Model/generated_music.mid'
    #generated_music_midi.write(output_path)
    #Save the generated MIDI to a temporary file
    def save_midi_to_tempfile(midi_data):
        temp_path = "temp.mid"
        midi_data.write(temp_path)
        return temp_path


    temp_midi_path = save_midi_to_tempfile(generated_music_midi)
    output_path = "output.wav"
    midi_to_wav(temp_midi_path, output_path)

    # Display the WAV audio in Streamlit
    audio_bytes = open(output_path, 'rb').read()
    st.audio(audio_bytes, format='audio/wav')