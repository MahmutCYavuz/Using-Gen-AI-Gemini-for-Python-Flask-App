document.querySelector('.submit-button').addEventListener('click', function(event) {
    event.preventDefault(); // Formun hemen gönderilmesini engelle
    this.classList.add('clicked');
    setTimeout(() => {
        // Burada formun gönderilmesini sağlayabilirsiniz
        // Örneğin: document.querySelector('.login-form').submit();
    }, 1000); // 1 saniye sonra formu gönder
});