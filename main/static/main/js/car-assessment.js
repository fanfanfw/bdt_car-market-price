function updateRangeValue(slider, valueId) {
    document.getElementById(valueId).textContent = slider.value + '%';
}

// Load categories on page load
document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
});

async function loadCategories() {
    try {
        const response = await fetch('/api/categories/');
        const categories = await response.json();
        
        const categorySelect = document.getElementById('category');
        categorySelect.innerHTML = '<option value="">Pilih Kategori</option>';
        
        categories.forEach(category => {
            categorySelect.innerHTML += `<option value="${category}">${category}</option>`;
        });
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

// Category change handler
document.getElementById('category').addEventListener('change', async function() {
    const category = this.value;
    const brandSelect = document.getElementById('brand');
    
    if (category) {
        try {
            const response = await fetch(`/api/brands/?category=${category}`);
            const brands = await response.json();
            
            brandSelect.innerHTML = '<option value="">Pilih Brand</option>';
            brands.forEach(brand => {
                brandSelect.innerHTML += `<option value="${brand}">${brand}</option>`;
            });
            
            brandSelect.disabled = false;
            resetSelects(['model', 'variant', 'year']);
        } catch (error) {
            console.error('Error loading brands:', error);
        }
    } else {
        brandSelect.disabled = true;
        resetSelects(['brand', 'model', 'variant', 'year']);
    }
});

// Brand change handler
document.getElementById('brand').addEventListener('change', async function() {
    const brand = this.value;
    const modelSelect = document.getElementById('model');
    
    if (brand) {
        try {
            const response = await fetch(`/api/models/?brand=${brand}`);
            const models = await response.json();
            
            modelSelect.innerHTML = '<option value="">Pilih Model</option>';
            models.forEach(model => {
                modelSelect.innerHTML += `<option value="${model}">${model}</option>`;
            });
            
            modelSelect.disabled = false;
            resetSelects(['variant', 'year']);
        } catch (error) {
            console.error('Error loading models:', error);
        }
    } else {
        resetSelects(['model', 'variant', 'year']);
    }
});

// Model change handler
document.getElementById('model').addEventListener('change', async function() {
    const brand = document.getElementById('brand').value;
    const model = this.value;
    const variantSelect = document.getElementById('variant');
    
    if (brand && model) {
        try {
            const response = await fetch(`/api/variants/?brand=${brand}&model=${model}`);
            const variants = await response.json();
            
            variantSelect.innerHTML = '<option value="">Pilih Variant</option>';
            variants.forEach(variant => {
                variantSelect.innerHTML += `<option value="${variant}">${variant}</option>`;
            });
            
            variantSelect.disabled = false;
            resetSelects(['year']);
        } catch (error) {
            console.error('Error loading variants:', error);
        }
    } else {
        resetSelects(['variant', 'year']);
    }
});

// Variant change handler
document.getElementById('variant').addEventListener('change', async function() {
    const brand = document.getElementById('brand').value;
    const model = document.getElementById('model').value;
    const variant = this.value;
    const yearSelect = document.getElementById('year');
    
    if (brand && model && variant) {
        try {
            const response = await fetch(`/api/years/?brand=${brand}&model=${model}&variant=${variant}`);
            const years = await response.json();
            
            yearSelect.innerHTML = '<option value="">Pilih Tahun</option>';
            years.forEach(year => {
                yearSelect.innerHTML += `<option value="${year}">${year}</option>`;
            });
            
            yearSelect.disabled = false;
        } catch (error) {
            console.error('Error loading years:', error);
        }
    } else {
        resetSelects(['year']);
    }
});

function resetSelects(selectIds) {
    selectIds.forEach(id => {
        const select = document.getElementById(id);
        select.innerHTML = `<option value="">Pilih ${id.charAt(0).toUpperCase() + id.slice(1)}</option>`;
        select.disabled = true;
    });
}

// Form submission with validation
document.getElementById('assessmentForm').addEventListener('submit', function(e) {
    const phone = document.querySelector('input[name="phone"]').value;
    
    if (!phone || phone.length < 10) {
        e.preventDefault();
        Swal.fire({
            icon: 'warning',
            title: 'Nomor HP Diperlukan',
            text: 'Silakan masukkan nomor HP yang valid untuk menerima hasil analisa.',
            confirmButtonText: 'OK'
        });
        return false;
    }

    // Show loading
    Swal.fire({
        title: 'Memproses...',
        text: 'Sedang menghitung perkiraan harga mobil Anda',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
});