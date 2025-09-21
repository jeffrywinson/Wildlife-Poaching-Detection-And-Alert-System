document.addEventListener('DOMContentLoaded', () => {
    const imageUpload = document.getElementById('image-upload');
    const imagePreview = document.getElementById('image-preview');
    const resultImage = document.getElementById('result-image');
    const detectBtn = document.getElementById('detect-btn');
    const loader = document.querySelector('.loader');

    let uploadedFile = null;

    imageUpload.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            uploadedFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.src = e.target.result;
                imagePreview.style.display = 'block';
                resultImage.src = '#'; // Reset result
                detectBtn.disabled = false;
            };
            reader.readAsDataURL(file);
        }
    });

    detectBtn.addEventListener('click', async () => {
    if (!uploadedFile) {
        alert('Please upload an image first!');
        return;
    }

    loader.classList.remove('hidden');
    detectBtn.disabled = true;
    resultImage.src = '#';

    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
        // This line must match the route in app.py
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData,
        });

        if (response.ok) {
            const imageBlob = await response.blob();
            const imageUrl = URL.createObjectURL(imageBlob);
            resultImage.src = imageUrl;
            resultImage.style.display = 'block';
        } else {
            // This is what's causing the alert pop-up
            const errorText = await response.text();
            alert(`Error: ${errorText}`);
        }
    } catch (error) {
        console.error('Error during fetch:', error);
        alert('An error occurred while processing the image.');
    } finally {
        loader.classList.add('hidden');
        detectBtn.disabled = false;
    }
});
});