document.addEventListener('DOMContentLoaded', function() {
    const inputText = document.getElementById('input_text');
    const submitButton = document.querySelector('.submit-button');
    const form = document.getElementById('analysis-form');
    const infoBox = document.getElementById('info-box');
    const infoIcon = document.getElementById('info-icon');
    const loadingAnimation = document.getElementById('loading-animation');
    const resultContainer = document.querySelector('.result-container');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileIcon = document.getElementById('file-icon');
    const fileName = document.getElementById('file-name');
    const tabs = document.getElementById('tabs');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const warningMessage = document.getElementById('warning-message');
    
    function toggleInfoBox() {
    if (infoBox.classList.contains('minimized')) {
        infoBox.classList.remove('minimized');
        setTimeout(() => {
            infoBox.style.display = 'block';
        }, 300); // Match the transition duration
        // infoIcon.style.display = '';
    } else {
        infoBox.classList.add('minimized');
        setTimeout(() => {
            infoBox.style.display = 'none';
        }, 300); // Match the transition duration
        infoIcon.style.display = 'block';
    }
}

    let timerInterval;
    let startTime;
    let elapsedTime = 0; // Elapsed time variable
    
    function startTimer() {
        startTime = Date.now();
        timerInterval = setInterval(() => {
            elapsedTime = (Date.now() - startTime) / 1000;
            document.getElementById('timer').textContent = elapsedTime.toFixed(2);
        }, 10);
        console.log("Timer başlatıldı");
    }
    
    function stopTimer() {
        clearInterval(timerInterval);
        console.log("Timer durdu, süre:", elapsedTime.toFixed(2));
        // Store the elapsed time in local storage
        localStorage.setItem('elapsedTime', elapsedTime.toFixed(2));
    }

    function updateSubmitButton() {
        if (inputText.value.trim().length > 0 || fileInput.files.length > 0) {
            submitButton.removeAttribute('disabled');
            submitButton.classList.add('active');
            inputText.removeAttribute('disabled');
        } else {
            submitButton.setAttribute('disabled', 'disabled');
            submitButton.classList.remove('active');
            inputText.setAttribute('disabled', 'disabled');
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

    inputText.addEventListener('focus', () => {
        if (!infoBox.classList.contains('minimized')) {
            toggleInfoBox(true);
        }
    });

    infoIcon.addEventListener('click', () => {
        toggleInfoBox();
    });

    document.addEventListener('click', (e) => {
        if (!infoBox.contains(e.target) && !infoIcon.contains(e.target) && !inputText.contains(e.target)) {
            if (!infoBox.classList.contains('minimized')) {
                toggleInfoBox(true);
            }
        }
    });
      // Function to display warning message
      function displayWarning(message) {
        warningMessage.textContent = message;
        warningMessage.classList.add('visible');
    }

    // Example of handling API response
    function handleApiResponse(response) {
        try {
            // Assume response is an object with a 'data' property
            if (!response.data || typeof response.data !== 'object') {
                throw new Error('Unexpected response format');
            }
            // Process the response data
            // ...
        } catch (error) {
            displayWarning('API yanıtı beklenen formatta değil. Lütfen daha sonra tekrar deneyin.');
        }
    }

    // Form gönderim olay dinleyicisini değiştirin
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        if (!submitButton.hasAttribute('disabled')) {
            startTimer(); // Timer'ı başlat
            infoBox.style.display = 'none';
            loadingAnimation.style.display = 'block';
            resultContainer.style.display = 'none';
            tabs.style.display = 'none';
            
            // Form verilerini al
            const formData = new FormData(form);
            
            // AJAX ile formu gönder
            fetch('/index', {
                method: 'POST',
                body: formData
            })
            .then(response => response.text())
            .then(html => {
                stopTimer(); // Timer'ı durdur
                console.log("Yanıt alındı, timer durmalı");
                
                // Sayfayı yenile, ama geçmişi değiştirmeden
                document.open();
                document.write(html);
                document.close();
                
                // Yükleme animasyonunu gizle
                loadingAnimation.style.display = 'none';
                infoBox.style.display = 'none';
    
                // Retrieve the elapsed time from local storage and display it
                const storedElapsedTime = localStorage.getItem('elapsedTime');
                if (storedElapsedTime) {
                    document.getElementById('timer').textContent = storedElapsedTime;
                }
    
            })
            .catch(error => {
                console.error('Hata:', error);
                stopTimer(); // Timer'ı durdur
                loadingAnimation.style.display = 'none';
            });
        }
    });
    
    inputText.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!submitButton.hasAttribute('disabled')) {
                submitButton.click(); // Submit butonuna tıklama işlemini tetikle
            }
        }
    });
    
    fileInput.addEventListener('change', () => {
        fileInfo.innerHTML = ''; // Önceki dosya bilgilerini temizle
        if (fileInput.files.length > 0) {
            Array.from(fileInput.files).forEach(file => {
                const fileType = file.type;
                const fileBox = document.createElement('div');
                fileBox.classList.add('file-box');
    
                const icon = document.createElement('img');
                if (fileType === 'application/pdf') {
                    icon.src = "/static/image/pdf_icon.png";
                } else if (fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || fileType === 'application/msword') {
                    icon.src = "/static/image/word_icon.png";
                } else {
                    icon.src = "/static/image/file_icon.png";
                }
                icon.classList.add('file-icon');
    
                const name = document.createElement('span');
                name.textContent = file.name;
                name.classList.add('file-name');
    
                // Dosya silme butonu ekle
                const deleteButton = document.createElement('button');
                deleteButton.innerHTML = '&times;'; // × işareti
                deleteButton.classList.add('file-delete-btn');
                deleteButton.addEventListener('click', () => {
                    fileBox.remove();
                    // Dosyayı FileList'ten kaldırma
                    const newFileList = Array.from(fileInput.files).filter(f => f.name !== file.name);
                    const dataTransfer = new DataTransfer();
                    newFileList.forEach(f => dataTransfer.items.add(f));
                    fileInput.files = dataTransfer.files;
                    
                    updateSubmitButton();
                    if (fileInput.files.length === 0) {
                        fileInfo.style.display = 'none';
                    }
                });
    
                fileBox.appendChild(icon);
                fileBox.appendChild(name);
                fileBox.appendChild(deleteButton);
                fileInfo.appendChild(fileBox);
            });
    
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

    // Sonuç geldiğinde sekmeleri göster ve bilgi kutusunu gizle
    if (resultContainer.innerHTML.trim() !== '') {
        tabs.style.display = 'flex';
        infoBox.style.display = 'none';
    }
});