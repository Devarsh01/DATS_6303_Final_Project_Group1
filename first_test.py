#%%
import numpy as np
import pretty_midi
import os
import tensorflow as tf
from tensorflow.keras.layers import Input, Embedding, Conv1D, BatchNormalization, LSTM, Dense, Softmax, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import LearningRateScheduler
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical

# Check for GPU availability
print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))
if tf.config.experimental.list_physical_devices('GPU'):
    print("Using GPU")
else:
    print("Using CPU")


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

def create_input_target_sequences(sequence, seq_length):
    """Create input and target sequences from detailed note sequences."""
    input_sequences = []
    target_sequences = []
    for i in range(len(sequence) - seq_length):
        # input_seq = [[event['pitch'], event['velocity'], event['start'], event['end']] for event in sequence[i:i+seq_length]]
        # target_seq = [[event['pitch'], event['velocity'], event['start'], event['end']] for event in sequence[i+1:i+1+seq_length]]
        input_seq = [[event['pitch']] for event in sequence[i:i + seq_length]]
        target_pitch = sequence[i + seq_length]['pitch']
        target_seq = to_categorical(target_pitch, num_classes=vocab_size)
        input_sequences.append(input_seq)
        target_sequences.append(target_seq)
    print(len(input_sequences))
    print(input_sequences[0])
    return np.array(input_sequences), np.array(target_sequences)

#%%
def build_model(seq_length, vocab_size, embedding_dim):
    inputs = Input(shape=(seq_length,))

    # Embedding layer: Converts input sequence of token indices to sequences of vectors
    x = Embedding(input_dim=vocab_size, output_dim=embedding_dim, input_length=seq_length)(inputs)

    # LSTM layer: You can stack more LSTM layers or adjust the number of units
    x = LSTM(units=256, return_sequences=True)(x)  # return_sequences=True if next layer is also RNN
    x = LSTM(units=256)(x)  # Last LSTM layer does not return sequences

    # Output layer: Linear layer (Dense) with 'vocab_size' units to predict the next pitch
    outputs = Dense(vocab_size, activation='softmax')(x)  # Using softmax for output distribution

    # Create and compile model
    model = Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model


# Directory containing MIDI files
directory = '/home/ubuntu/Devarsh_DL/Project/DL_Dataset/bach/'

# Load and preprocess data

seq_length = 30  # Length of the input sequences
vocab_size = 128  # Number of unique pitches (for MIDI, typically 128)
embedding_dim = 100 # Define the length of sequences for input and target
sequences = load_midi_details(directory)
input_sequences, target_sequences = create_input_target_sequences(sequences, seq_length)


print("Input sequences shape:", input_sequences.shape)
print("Target sequences shape:", target_sequences.shape)

# Recreate and compile the model
model = build_model(seq_length, vocab_size, embedding_dim)
model.summary()
model.fit(input_sequences, target_sequences, epochs=50, batch_size=32)

#%%
def generate_music(model, seed_sequence, length=10, steps_per_second=5):
    """Generate music from a seed sequence aiming for a total duration."""
    # Ensure the seed sequence is of the correct length

    generated_sequence = np.copy(seed_sequence)  # Copy to avoid modifying the original seed
    total_steps = length * steps_per_second  # Total steps needed for desired duration
    # print(f"Total steps to generate: {total_steps}")

    for _ in range(total_steps):
        # Predict the next step using the last 'seq_length' elements in the generated_sequence
        prediction = model.predict(np.expand_dims(generated_sequence[-seq_length:], axis=0))[0]
        # print('Prediction vector:', prediction)

        # Select the pitch with the highest probability
        predicted_pitch = np.argmax(prediction)
        # print('Predicted pitch:', predicted_pitch)

        # Normalize the predicted pitch and reshape for stacking
        # normalized_pitch = np.array([[predicted_pitch / 127]])

        # Append the normalized pitch to the generated sequence
        generated_sequence = np.vstack([generated_sequence, predicted_pitch])
        # print('Updated generated sequence:', generated_sequence)
    print("This is damnn great generation!!!", generated_sequence[-30:])
    return generated_sequence


#%%
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

# Assuming you have a trained model and a seed sequence
# seed_pitches = np.array([60, 62, 64, 65, 67, 61, 45, 55, 47, 68])  # Example MIDI pitches
seed_pitches = input_sequences[3000]
# Normalize the pitches and reshape for model input
# Normalize by dividing by the maximum MIDI pitch value (127)
# Reshape to match expected model input shape (n, 1)
seed_sequence = (seed_pitches).reshape(-1, 1)  # Reshape to (n, 1)

# Call the generate_music function with the reshaped and normalized seed sequence
generated_music = generate_music(model, seed_sequence, length=20, steps_per_second=2)   # Generate enough steps
generated_music_midi = generated_to_midi(generated_music, total_duration=8)
generated_music_midi.write('/home/ubuntu/Devarsh_DL/Project/gen_music/output_midi_file_4.mid')


