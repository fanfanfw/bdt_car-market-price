// Car Price Estimator JavaScript with OTP Integration
// Based on the reference design with enhanced functionality

let verifiedPhone = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    loadBrands();
    setupEventListeners();
    setupFormValidation();
}

// Load brands on page load
async function loadBrands() {
    try {
        const response = await fetch(API_URLS.brands);
        const brands = await response.json();
        
        const brandSelect = document.getElementById('brandSelect');
        brandSelect.innerHTML = '<option value="" disabled selected>Select Brand</option>';
        
        brands.forEach(brand => {
            brandSelect.innerHTML += `<option value="${brand}">${brand}</option>`;
        });
        
        brandSelect.disabled = false;
    } catch (error) {
        console.error('Error loading brands:', error);
        showError('Failed to load brand. Please refresh the page.');
    }
}

// Setup all event listeners
function setupEventListeners() {
    // Brand change handler
    document.getElementById('brandSelect').addEventListener('change', async function() {
        const brand = this.value;
        const modelSelect = document.getElementById('modelSelect');
        
        if (brand) {
            try {
                showLoading(modelSelect);
                const response = await fetch(`${API_URLS.models}?brand=${encodeURIComponent(brand)}`);
                const models = await response.json();
                
                modelSelect.innerHTML = '<option value="" disabled selected>Select Model</option>';
                models.forEach(model => {
                    modelSelect.innerHTML += `<option value="${model}">${model}</option>`;
                });
                
                modelSelect.disabled = false;
                resetSelects(['variantSelect', 'yearSelect']);
                validateForm();
            } catch (error) {
                console.error('Error loading models:', error);
                showError('Failed to load model. Please try again.');
            }
        } else {
            resetSelects(['modelSelect', 'variantSelect', 'yearSelect']);
            validateForm();
        }
    });

    // Model change handler
    document.getElementById('modelSelect').addEventListener('change', async function() {
        const brand = document.getElementById('brandSelect').value;
        const model = this.value;
        const variantSelect = document.getElementById('variantSelect');
        
        if (brand && model) {
            try {
                showLoading(variantSelect);
                const response = await fetch(`${API_URLS.variants}?brand=${encodeURIComponent(brand)}&model=${encodeURIComponent(model)}`);
                const variants = await response.json();
                
                variantSelect.innerHTML = '<option value="" disabled selected>Select Variant</option>';
                variants.forEach(variant => {
                    variantSelect.innerHTML += `<option value="${variant}">${variant}</option>`;
                });
                
                variantSelect.disabled = false;
                resetSelects(['yearSelect']);
                validateForm();
            } catch (error) {
                console.error('Error loading variants:', error);
                showError('Failed to load variant. Please try again.');
            }
        } else {
            resetSelects(['variantSelect', 'yearSelect']);
            validateForm();
        }
    });

    // Variant change handler
    document.getElementById('variantSelect').addEventListener('change', async function() {
        const brand = document.getElementById('brandSelect').value;
        const model = document.getElementById('modelSelect').value;
        const variant = this.value;
        const yearSelect = document.getElementById('yearSelect');
        
        if (brand && model && variant) {
            try {
                showLoading(yearSelect);
                const response = await fetch(`${API_URLS.years}?brand=${encodeURIComponent(brand)}&model=${encodeURIComponent(model)}&variant=${encodeURIComponent(variant)}`);
                const years = await response.json();
                
                yearSelect.innerHTML = '<option value="" disabled selected>Select Year</option>';
                years.forEach(year => {
                    yearSelect.innerHTML += `<option value="${year}">${year}</option>`;
                });
                
                yearSelect.disabled = false;
                validateForm();
            } catch (error) {
                console.error('Error loading years:', error);
                showError('Failed to load year. Please try again.');
            }
        } else {
            resetSelects(['yearSelect']);
            validateForm();
        }
    });

    // Year change handler
    document.getElementById('yearSelect').addEventListener('change', validateForm);

    // Radio button change handlers
    const radioButtons = document.querySelectorAll('input[type="radio"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', validateForm);
    });

    // Mileage input handler
    document.getElementById('userMileageInput').addEventListener('input', validateForm);
}

function resetSelects(selectIds) {
    selectIds.forEach(id => {
        const select = document.getElementById(id);
        if (select) {
            const placeholder = getPlaceholderText(id);
            select.innerHTML = `<option value="" disabled selected>${placeholder}</option>`;
            select.disabled = true;
        }
    });
}

function getPlaceholderText(selectId) {
    const placeholders = {
        'brandSelect': 'Select Brand',
        'modelSelect': 'Select Model', 
        'variantSelect': 'Select Variant',
        'yearSelect': 'Select Year'
    };
    return placeholders[selectId] || 'Select';
}

function showLoading(selectElement) {
    selectElement.innerHTML = '<option value="" disabled selected>Loading...</option>';
    selectElement.disabled = true;
}

function validateForm() {
    const brand = document.getElementById('brandSelect').value;
    const model = document.getElementById('modelSelect').value;
    const variant = document.getElementById('variantSelect').value;
    const year = document.getElementById('yearSelect').value;
    
    // Check all required radio button groups dynamically
    const allRadioGroups = document.querySelectorAll('input[type="radio"][required]');
    const uniqueGroupNames = [...new Set(Array.from(allRadioGroups).map(radio => radio.name))];
    
    const allRadiosSelected = uniqueGroupNames.every(groupName => {
        return document.querySelector(`input[name="${groupName}"]:checked`) !== null;
    });
    
    const submitBtn = document.getElementById('submitBtn');
    const isValid = brand && model && variant && year && allRadiosSelected;
    
    submitBtn.disabled = !isValid;
    submitBtn.classList.toggle('disabled:opacity-50', !isValid);
    
    if (isValid) {
        submitBtn.classList.add('btn-primary');
        submitBtn.classList.remove('btn-disabled');
    } else {
        submitBtn.classList.remove('btn-primary');
        submitBtn.classList.add('btn-disabled');
    }
}

function setupFormValidation() {
    const form = document.getElementById('mileageForm');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!validateFormBeforeSubmit()) {
            return false;
        }
        
        // Show loading state
        showLoadingState();
        
        // Submit form
        submitForm();
    });
}

function validateFormBeforeSubmit() {
    const brand = document.getElementById('brandSelect').value;
    const model = document.getElementById('modelSelect').value;
    const variant = document.getElementById('variantSelect').value;
    const year = document.getElementById('yearSelect').value;
    
    if (!brand || !model || !variant || !year) {
        showError('Please complete all vehicle specifications.');
        return false;
    }
    
    // Check all required radio button groups dynamically
    const allRadioGroups = document.querySelectorAll('input[type="radio"][required]');
    const uniqueGroupNames = [...new Set(Array.from(allRadioGroups).map(radio => radio.name))];
    
    for (let groupName of uniqueGroupNames) {
        if (!document.querySelector(`input[name="${groupName}"]:checked`)) {
            showError(`Please select condition for ${getReadableFieldName(groupName)}.`);
            return false;
        }
    }
    
    return true;
}

function getReadableFieldName(fieldName) {
    // Try to get readable name from the DOM first
    const radioInput = document.querySelector(`input[name="${fieldName}"]`);
    if (radioInput) {
        const conditionCard = radioInput.closest('.card-body');
        if (conditionCard) {
            const titleElement = conditionCard.querySelector('h4');
            if (titleElement) {
                return titleElement.textContent.trim();
            }
        }
    }
    
    // Fallback: convert field name to readable format
    return fieldName.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function showLoadingState() {
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
        <span class="loading loading-spinner loading-sm mr-2"></span>
        Memproses...
    `;
    
    // Store original text for restoration if needed
    submitBtn.dataset.originalText = originalText;
}

function submitForm() {
    const form = document.getElementById('mileageForm');
    
    // Since we want to redirect to a new page, we'll submit normally
    // but first show a nice loading animation
    setTimeout(() => {
        form.submit();
    }, 1000); // Small delay to show loading state
}

function showError(message) {
    // Using SweetAlert2 which is available from base.html
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'error',
            title: 'Oops!',
            text: message,
            confirmButtonText: 'OK'
        });
    } else {
        // Fallback to alert if SweetAlert2 is not available
        alert(message);
    }
}

function showSuccess(message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: message,
            confirmButtonText: 'OK'
        });
    } else {
        alert(message);
    }
}

// Utility functions for enhanced UX
function addHoverEffects() {
    // Add hover effects to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-lg');
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-lg');
            this.style.transform = 'translateY(0)';
        });
    });
}

// Initialize hover effects when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(addHoverEffects, 100); // Small delay to ensure all elements are rendered
});

// Add smooth scrolling for better UX
function smoothScrollToElement(element) {
    element.scrollIntoView({ 
        behavior: 'smooth',
        block: 'center'
    });
}

// Enhanced error handling with retry functionality
function handleApiError(error, retryCallback = null) {
    console.error('API Error:', error);
    
    let message = 'Terjadi kesalahan saat memuat data.';
    if (error.message) {
        message += ` Detail: ${error.message}`;
    }
    
    if (retryCallback && typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'error',
            title: 'Kesalahan Jaringan',
            text: message,
            showCancelButton: true,
            confirmButtonText: 'Coba Lagi',
            cancelButtonText: 'Batal'
        }).then((result) => {
            if (result.isConfirmed) {
                retryCallback();
            }
        });
    } else {
        showError(message);
    }
}

