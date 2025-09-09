// Alpine.js Components for Admin Dashboard
// Modern replacement for jQuery + DataTables

// Data Table Component
function dataTable(config) {
    return {
        // Core data
        data: [],
        filteredData: [],
        loading: false,
        error: null,
        
        // Pagination
        currentPage: 1,
        pageSize: 25,
        totalPages: 1,
        totalRecords: 0,
        
        // Sorting
        sortField: null,
        sortDirection: 'asc',
        
        // Searching & Filtering
        search: '',
        filters: {},
        
        // Configuration
        config: {
            apiUrl: '',
            columns: [],
            serverSide: false,
            ...config
        },
        
        // Initialize
        async init() {
            await this.loadData();
            this.calculatePagination();
        },
        
        // Load data from API
        async loadData(params = {}) {
            this.loading = true;
            this.error = null;
            
            try {
                const queryParams = new URLSearchParams({
                    page: this.currentPage,
                    size: this.pageSize,
                    search: this.search,
                    sort: this.sortField || '',
                    direction: this.sortDirection,
                    ...this.filters,
                    ...params
                });
                
                const response = await fetch(`${this.config.apiUrl}?${queryParams}`);
                const result = await response.json();
                
                if (this.config.serverSide) {
                    this.data = result.data || [];
                    this.totalRecords = result.total || 0;
                    this.filteredData = this.data;
                } else {
                    this.data = result.data || result || [];
                    this.applyFilters();
                }
                
                this.calculatePagination();
            } catch (error) {
                console.error('Error loading data:', error);
                this.error = 'Failed to load data';
            } finally {
                this.loading = false;
            }
        },
        
        // Apply client-side filters
        applyFilters() {
            let filtered = [...this.data];
            
            // Search
            if (this.search) {
                const searchTerm = this.search.toLowerCase();
                filtered = filtered.filter(item => 
                    Object.values(item).some(value => 
                        String(value).toLowerCase().includes(searchTerm)
                    )
                );
            }
            
            // Additional filters
            Object.entries(this.filters).forEach(([key, value]) => {
                if (value) {
                    filtered = filtered.filter(item => 
                        String(item[key]).toLowerCase().includes(String(value).toLowerCase())
                    );
                }
            });
            
            this.filteredData = filtered;
            this.totalRecords = filtered.length;
        },
        
        // Sorting
        sort(field) {
            if (this.sortField === field) {
                this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
            } else {
                this.sortField = field;
                this.sortDirection = 'asc';
            }
            
            if (this.config.serverSide) {
                this.loadData();
            } else {
                this.filteredData.sort((a, b) => {
                    let valueA = a[field];
                    let valueB = b[field];
                    
                    // Handle numbers
                    if (!isNaN(valueA) && !isNaN(valueB)) {
                        valueA = parseFloat(valueA);
                        valueB = parseFloat(valueB);
                    }
                    
                    if (this.sortDirection === 'asc') {
                        return valueA > valueB ? 1 : -1;
                    } else {
                        return valueA < valueB ? 1 : -1;
                    }
                });
            }
        },
        
        // Pagination
        calculatePagination() {
            this.totalPages = Math.ceil(this.totalRecords / this.pageSize);
        },
        
        get paginatedData() {
            if (this.config.serverSide) {
                return this.filteredData;
            }
            
            const start = (this.currentPage - 1) * this.pageSize;
            const end = start + this.pageSize;
            return this.filteredData.slice(start, end);
        },
        
        // Navigation
        goToPage(page) {
            if (page >= 1 && page <= this.totalPages) {
                this.currentPage = page;
                if (this.config.serverSide) {
                    this.loadData();
                }
            }
        },
        
        nextPage() {
            this.goToPage(this.currentPage + 1);
        },
        
        prevPage() {
            this.goToPage(this.currentPage - 1);
        },
        
        // Search
        async performSearch() {
            if (this.config.serverSide) {
                this.currentPage = 1;
                await this.loadData();
            } else {
                this.applyFilters();
                this.currentPage = 1;
                this.calculatePagination();
            }
        },
        
        // Utility functions
        get pageInfo() {
            const start = (this.currentPage - 1) * this.pageSize + 1;
            const end = Math.min(this.currentPage * this.pageSize, this.totalRecords);
            return `${start}-${end} of ${this.totalRecords}`;
        },
        
        get pageNumbers() {
            const pages = [];
            const maxPages = 5;
            let startPage = Math.max(1, this.currentPage - Math.floor(maxPages / 2));
            let endPage = Math.min(this.totalPages, startPage + maxPages - 1);
            
            if (endPage - startPage + 1 < maxPages) {
                startPage = Math.max(1, endPage - maxPages + 1);
            }
            
            for (let i = startPage; i <= endPage; i++) {
                pages.push(i);
            }
            
            return pages;
        }
    }
}

// Modal Component
function modal() {
    return {
        show: false,
        title: '',
        content: '',
        
        open(title = '', content = '') {
            this.title = title;
            this.content = content;
            this.show = true;
            document.body.classList.add('overflow-hidden');
        },
        
        close() {
            this.show = false;
            document.body.classList.remove('overflow-hidden');
        }
    }
}

// Form Component
function form(config = {}) {
    return {
        data: {},
        errors: {},
        loading: false,
        
        config: {
            url: '',
            method: 'POST',
            ...config
        },
        
        init() {
            this.data = { ...this.config.defaultData || {} };
        },
        
        async submit() {
            this.loading = true;
            this.errors = {};
            
            try {
                const response = await fetch(this.config.url, {
                    method: this.config.method,
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify(this.data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.$dispatch('form-success', result);
                } else {
                    this.errors = result.errors || {};
                    throw new Error(result.error || 'Validation failed');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                this.$dispatch('form-error', { error: error.message });
            } finally {
                this.loading = false;
            }
        },
        
        reset() {
            this.data = { ...this.config.defaultData || {} };
            this.errors = {};
        },
        
        getCsrfToken() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                   this.getCookie('csrftoken');
        },
        
        getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    }
}

// Export components for global use
window.AlpineComponents = {
    dataTable,
    modal,
    form
};