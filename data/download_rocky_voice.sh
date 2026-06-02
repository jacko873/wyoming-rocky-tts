#!/bin/bash

# Download the Rocky reference voice
echo "Downloading Rocky reference voice..."
wget -O rocky_reference.wav "https://pedramamini.com/dropbox/rocky_training_audio_scrubbed.wav"

if [ $? -eq 0 ]; then
    echo "✓ Rocky voice downloaded successfully"
    echo "File saved as: rocky_reference.wav"
    echo "Size: $(du -h rocky_reference.wav | cut -f1)"
else
    echo "✗ Failed to download Rocky voice"
    exit 1
fi