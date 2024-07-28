document.getElementById('file-upload').addEventListener('change', function (event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('file-name').textContent = file.name;
        document.getElementById('file-info').style.display = 'flex';
        document.getElementById('text-area').style.height = '100px';
    }
});

document.getElementById('remove-file').addEventListener('click', function () {
    document.getElementById('file-upload').value = '';
    document.getElementById('file-info').style.display = 'none';
    document.getElementById('text-area').style.height = '60px';
});

document.getElementById('text-area').addEventListener('input', function () {
    const text = document.getElementById('text-area').value;
    const submitButton = document.getElementById('submit-button');
    if (text.trim()) {
        submitButton.classList.add('active');
    } else {
        submitButton.classList.remove('active');
    }
});
