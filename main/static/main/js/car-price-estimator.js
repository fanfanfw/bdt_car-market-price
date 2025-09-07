// Car Price Estimator JavaScript with OTP Integration
// Based on the reference design with enhanced functionality

let verifiedPhone = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    loadCategories();
    setupEventListeners();
    setupFormValidation();
}

// Load categories on page load
async function loadCategories() {
    try {
        const response = await fetch(API_URLS.categories);
        const categories = await response.json();
        
        const categorySelect = document.getElementById('categorySelect');
        categorySelect.innerHTML = '<option value="" disabled selected>Pilih Category</option>';
        
        categories.forEach(category => {
            categorySelect.innerHTML += `<option value="${category}">${category}</option>`;
        });
    } catch (error) {
        console.error('Error loading categories:', error);
        showError('Gagal memuat kategori. Silakan refresh halaman.');
    }
}

// Setup all event listeners
function setupEventListeners() {
    // Category change handler
    document.getElementById('categorySelect').addEventListener('change', async function() {
        const category = this.value;
        const brandSelect = document.getElementById('brandSelect');
        
        if (category) {
            try {
                showLoading(brandSelect);
                const response = await fetch(`${API_URLS.brands}?category=${encodeURIComponent(category)}`);
                const brands = await response.json();
                
                brandSelect.innerHTML = '<option value="" disabled selected>Pilih Brand</option>';
                brands.forEach(brand => {
                    brandSelect.innerHTML += `<option value="${brand}">${brand}</option>`;
                });
                
                brandSelect.disabled = false;
                resetSelects(['modelSelect', 'variantSelect', 'yearSelect']);
                validateForm();
            } catch (error) {
                console.error('Error loading brands:', error);
                showError('Gagal memuat brand. Silakan coba lagi.');
            }
        } else {
            brandSelect.disabled = true;
            resetSelects(['brandSelect', 'modelSelect', 'variantSelect', 'yearSelect']);
            validateForm();
        }
    });

    // Brand change handler
    document.getElementById('brandSelect').addEventListener('change', async function() {
        const brand = this.value;
        const modelSelect = document.getElementById('modelSelect');
        
        if (brand) {
            try {
                showLoading(modelSelect);
                const response = await fetch(`${API_URLS.models}?brand=${encodeURIComponent(brand)}`);
                const models = await response.json();
                
                modelSelect.innerHTML = '<option value="" disabled selected>Pilih Model</option>';
                models.forEach(model => {
                    modelSelect.innerHTML += `<option value="${model}">${model}</option>`;
                });
                
                modelSelect.disabled = false;
                resetSelects(['variantSelect', 'yearSelect']);
                validateForm();
            } catch (error) {
                console.error('Error loading models:', error);
                showError('Gagal memuat model. Silakan coba lagi.');
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
                
                variantSelect.innerHTML = '<option value="" disabled selected>Pilih Variant</option>';
                variants.forEach(variant => {
                    variantSelect.innerHTML += `<option value="${variant}">${variant}</option>`;
                });
                
                variantSelect.disabled = false;
                resetSelects(['yearSelect']);
                validateForm();
            } catch (error) {
                console.error('Error loading variants:', error);
                showError('Gagal memuat variant. Silakan coba lagi.');
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
                
                yearSelect.innerHTML = '<option value="" disabled selected>Pilih Tahun</option>';
                years.forEach(year => {
                    yearSelect.innerHTML += `<option value="${year}">${year}</option>`;
                });
                
                yearSelect.disabled = false;
                validateForm();
            } catch (error) {
                console.error('Error loading years:', error);
                showError('Gagal memuat tahun. Silakan coba lagi.');
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
        'brandSelect': 'Pilih Brand',
        'modelSelect': 'Pilih Model', 
        'variantSelect': 'Pilih Variant',
        'yearSelect': 'Pilih Tahun'
    };
    return placeholders[selectId] || 'Pilih';
}

function showLoading(selectElement) {
    selectElement.innerHTML = '<option value="" disabled selected>Loading...</option>';
    selectElement.disabled = true;
}

function validateForm() {
    const category = document.getElementById('categorySelect').value;
    const brand = document.getElementById('brandSelect').value;
    const model = document.getElementById('modelSelect').value;
    const variant = document.getElementById('variantSelect').value;
    const year = document.getElementById('yearSelect').value;
    
    // Check all required radio button groups
    const requiredRadioGroups = [
        'exterior_condition',
        'interior_condition', 
        'mechanical_condition',
        'accident_history',
        'service_history',
        'number_of_owners',
        'tires_brakes',
        'modifications',
        'market_demand',
        'brand_category',
        'price_tier'
    ];
    
    const allRadiosSelected = requiredRadioGroups.every(groupName => {
        return document.querySelector(`input[name="${groupName}"]:checked`) !== null;
    });
    
    const submitBtn = document.getElementById('submitBtn');
    const isValid = category && brand && model && variant && year && allRadiosSelected;
    
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
    const category = document.getElementById('categorySelect').value;
    const brand = document.getElementById('brandSelect').value;
    const model = document.getElementById('modelSelect').value;
    const variant = document.getElementById('variantSelect').value;
    const year = document.getElementById('yearSelect').value;
    
    if (!category || !brand || !model || !variant || !year) {
        showError('Silakan lengkapi semua spesifikasi kendaraan.');
        return false;
    }
    
    // Check all required radio button groups
    const requiredRadioGroups = [
        'exterior_condition',
        'interior_condition', 
        'mechanical_condition',
        'accident_history',
        'service_history',
        'number_of_owners',
        'tires_brakes',
        'modifications',
        'market_demand',
        'brand_category',
        'price_tier'
    ];
    
    for (let groupName of requiredRadioGroups) {
        if (!document.querySelector(`input[name="${groupName}"]:checked`)) {
            showError(`Silakan pilih kondisi untuk ${getReadableFieldName(groupName)}.`);
            return false;
        }
    }
    
    return true;
}

function getReadableFieldName(fieldName) {
    const fieldNames = {
        'exterior_condition': 'Exterior Condition',
        'interior_condition': 'Interior Condition',
        'mechanical_condition': 'Mechanical Condition',
        'accident_history': 'Accident History',
        'service_history': 'Service History',
        'number_of_owners': 'Number of Owners',
        'tires_brakes': 'Tires & Brakes',
        'modifications': 'Modifications',
        'market_demand': 'Market Demand',
        'brand_category': 'Brand Category',
        'price_tier': 'Price Tier'
    };
    return fieldNames[fieldName] || fieldName;
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
            title: 'Berhasil!',
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

