document.addEventListener('DOMContentLoaded', function() {
    // Toggle sidebar on mobile
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (sidebar && sidebar.classList.contains('active')) {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        }
    });
    
    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Bạn có chắc chắn muốn đăng xuất?')) {
                // Clear localStorage token
                localStorage.removeItem('access_token');
                // Redirect to logout endpoint which will clear the cookie
                window.location.href = '/logout';
            }
        });
    }
    
    // Confirm delete operations
    const deleteButtons = document.querySelectorAll('.delete-btn, [data-action="delete"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Bạn có chắc chắn muốn xóa mục này không?')) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        });
    });
    
    // Datatables initialization (if library is loaded)
    if (typeof $.fn.DataTable !== 'undefined') {
        $('.datatable').DataTable({
            language: {
                url: '//cdn.datatables.net/plug-ins/1.10.24/i18n/Vietnamese.json'
            },
            responsive: true
        });
    }
    
    // Toast notifications
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="${getIconForType(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="toast-close">&times;</button>
        `;
        
        document.body.appendChild(toast);
        
        // Show the toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);
        
        // Remove the toast after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 5000);
        
        // Close button functionality
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        });
    }
    
    function getIconForType(type) {
        switch (type) {
            case 'success': return 'fas fa-check-circle';
            case 'warning': return 'fas fa-exclamation-triangle';
            case 'error': return 'fas fa-times-circle';
            default: return 'fas fa-info-circle';
        }
    }
    
    // Expose functions globally
    window.adminUtils = {
        showToast: showToast
    };
    
    // Check for message in URL params (for toast notifications after redirects)
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    const messageType = urlParams.get('type') || 'info';
    
    if (message) {
        showToast(decodeURIComponent(message), messageType);
        
        // Remove message from URL without reloading the page
        const newUrl = window.location.pathname + 
            window.location.search.replace(/([&?])message=[^&]+(&|$)/, '$1').replace(/([&?])type=[^&]+(&|$)/, '$1')
                .replace(/[?&]$/, '');
        window.history.replaceState({}, document.title, newUrl);
    }
    
    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    // Add or show error message
                    let errorElement = field.nextElementSibling;
                    if (!errorElement || !errorElement.classList.contains('error-message')) {
                        errorElement = document.createElement('div');
                        errorElement.className = 'error-message';
                        errorElement.textContent = 'Trường này là bắt buộc';
                        field.parentNode.insertBefore(errorElement, field.nextSibling);
                    } else {
                        errorElement.style.display = 'block';
                    }
                } else {
                    field.classList.remove('is-invalid');
                    
                    // Hide error message if exists
                    const errorElement = field.nextElementSibling;
                    if (errorElement && errorElement.classList.contains('error-message')) {
                        errorElement.style.display = 'none';
                    }
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // AJAX form submission
    const ajaxForms = document.querySelectorAll('form[data-ajax]');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(form);
            const submitBtn = form.querySelector('[type="submit"]');
            const method = form.getAttribute('method').toUpperCase() || 'POST';
            const url = form.getAttribute('action');
            
            // Disable submit button and show loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang xử lý...';
            }
            
            // Convert FormData to JSON if needed
            const isJson = form.getAttribute('data-json') === 'true';
            let data = formData;
            
            if (isJson) {
                data = {};
                formData.forEach((value, key) => {
                    data[key] = value;
                });
                data = JSON.stringify(data);
            }
            
            // Make the AJAX request
            fetch(url, {
                method: method,
                body: isJson ? data : formData,
                headers: isJson ? {
                    'Content-Type': 'application/json'
                } : undefined,
                credentials: 'same-origin'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Show success message
                showToast(data.message || 'Thao tác thành công!', 'success');
                
                // Redirect if specified
                const redirect = form.getAttribute('data-redirect');
                if (redirect) {
                    window.location.href = redirect;
                    return;
                }
                
                // Reset form if needed
                const shouldReset = form.getAttribute('data-reset') !== 'false';
                if (shouldReset) {
                    form.reset();
                }
                
                // Call success callback if defined
                const successCallback = form.getAttribute('data-success');
                if (successCallback && typeof window[successCallback] === 'function') {
                    window[successCallback](data);
                }
                
                // Reload page if needed
                const shouldReload = form.getAttribute('data-reload') === 'true';
                if (shouldReload) {
                    window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Đã xảy ra lỗi: ' + error.message, 'error');
            })
            .finally(() => {
                // Re-enable submit button
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = submitBtn.getAttribute('data-original-text') || 'Lưu';
                }
            });
        });
        
        // Store original button text
        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
            submitBtn.setAttribute('data-original-text', submitBtn.innerHTML);
        }
    });
});