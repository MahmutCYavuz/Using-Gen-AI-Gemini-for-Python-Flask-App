document.addEventListener('DOMContentLoaded', function() {
    const inputText = document.getElementById('input_text');
    const submitButton = document.querySelector('.submit-button');
    const form = document.querySelector('.form');
    const loadingAnimation = document.getElementById('loading-animation');
    const resultContainer = document.querySelector('.result-container');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileIcon = document.getElementById('file-icon');
    const fileName = document.getElementById('file-name');
    const tabs = document.getElementById('tabs');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    function updateSubmitButton() {
        if (inputText.value.trim().length > 0 || fileInput.files.length > 0) {
            submitButton.removeAttribute('disabled');
            submitButton.classList.add('active');
        } else {
            submitButton.setAttribute('disabled', 'disabled');
            submitButton.classList.remove('active');
        }
    }

    function adjustTextareaHeight() {
        inputText.style.height = 'auto';
        const maxHeight = parseInt(window.getComputedStyle(inputText).lineHeight) * 7;
        if (inputText.scrollHeight > maxHeight) {
            inputText.style.height = maxHeight + 'px';
            inputText.style.overflowY = 'scroll';
        } else {
            inputText.style.height = inputText.scrollHeight + 'px';
            inputText.style.overflowY = 'hidden';
        }
    }

    inputText.addEventListener('input', () => {
        updateSubmitButton();
        adjustTextareaHeight();
    });
    
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        if (!submitButton.hasAttribute('disabled')) {
            loadingAnimation.style.display = 'block';
            resultContainer.style.display = 'none';
            tabs.style.display = 'none';
            form.submit();
        }
    });
    
    inputText.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!submitButton.hasAttribute('disabled')) {
                loadingAnimation.style.display = 'block';
                resultContainer.style.display = 'none';
                tabs.style.display = 'none';
                form.submit();
            }
        }
    });
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            const file = fileInput.files[0];
            fileName.textContent = file.name;
    
            const fileType = file.type;
            if (fileType === 'application/pdf') {
                fileIcon.src = "/static/image/pdf_icon.png";
            } else if (fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || fileType === 'application/msword') {
                fileIcon.src = "/static/image/word_icon.png";
            } else {
                fileIcon.src = "/static/image/file_icon.png";
            }
    
            fileInfo.style.display = 'flex';
        } else {
            fileInfo.style.display = 'none';
        }
        updateSubmitButton();
    });

    // Sonuç geldiğinde sekmeleri ve içeriği göster
    if (document.querySelector('.result-container').children.length > 0) {
        document.getElementById('tabs').style.display = 'flex';
        document.querySelector('.result-container').style.display = 'block';
        // İlk sekmeyi aktif yap
        document.querySelector('.tab-button').classList.add('active');
        document.querySelector('.tab-content').classList.add('active');
    }

    // Tab işlevselliği
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            button.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // Sonuç geldiğinde sekmeleri göster
    if (resultContainer.innerHTML.trim() !== '') {
        tabs.style.display = 'flex';
    }
});