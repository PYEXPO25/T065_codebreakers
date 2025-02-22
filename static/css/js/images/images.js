// Flash message timeout
setTimeout(function() {
    let flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => flash.style.display = 'none');
}, 3000);

// Confirm before deleting stock
function confirmDelete() {
    return confirm("Are you sure you want to delete this stock?");
}
