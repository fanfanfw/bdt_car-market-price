// Alpine.js Bundle
import Alpine from 'alpinejs'

// Make Alpine available globally
window.Alpine = Alpine

// Start Alpine
Alpine.start()

// Import and make components available globally after Alpine starts
document.addEventListener('DOMContentLoaded', () => {
    import('./alpine-components.js');
});