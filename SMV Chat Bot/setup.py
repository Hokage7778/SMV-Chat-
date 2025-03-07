import os

# Create directory structure
directories = [
    'app/static/audio/cache',
    'app/static/css',
    'app/static/js',
    'app/templates'
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

# Move files to their correct locations
file_moves = [
    ('index.html', 'app/templates/index.html'),
    ('styles.css', 'app/static/css/styles.css'),
    ('app.js', 'app/static/js/app.js')
]

for source, destination in file_moves:
    if os.path.exists(source):
        with open(source, 'r') as src_file:
            content = src_file.read()
            
        with open(destination, 'w') as dest_file:
            dest_file.write(content)
            
        print(f"Moved {source} to {destination}")
    else:
        print(f"Warning: {source} does not exist")

print("\nSetup complete! Run the application with: python app.py") 