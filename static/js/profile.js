// Profile Page JavaScript
class ProfileManager {
    constructor() {
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Edit Profile Form
        const editForm = document.getElementById('editProfileForm');
        if (editForm) {
            editForm.addEventListener('submit', this.handleEditProfile.bind(this));
        }

        // Change Password Form
        const passwordForm = document.getElementById('changePasswordForm');
        if (passwordForm) {
            passwordForm.addEventListener('submit', this.handleChangePassword.bind(this));
        }

        // Modal keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
    }

    openEditProfileModal() {
        const modal = new bootstrap.Modal(document.getElementById('editProfileModal'));
        modal.show();
    }

    openChangePasswordModal() {
        const modal = new bootstrap.Modal(document.getElementById('changePasswordModal'));
        modal.show();
    }

    togglePassword(inputId) {
        const input = document.getElementById(inputId);
        const icon = input.nextElementSibling.querySelector('i');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.remove('fa-eye');
            icon.classList.add('fa-eye-slash');
        } else {
            input.type = 'password';
            icon.classList.remove('fa-eye-slash');
            icon.classList.add('fa-eye');
        }
    }

    async handleEditProfile(e) {
        e.preventDefault();
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Đang lưu...';
        
        const formData = {
            full_name: document.getElementById('editFullName').value.trim(),
            email: document.getElementById('editEmail').value.trim(),
            phone_number: document.getElementById('editPhoneNumber').value.trim() || null,
            address: document.getElementById('editAddress').value.trim() || null
        };
        
        // Client-side validation
        if (!formData.full_name) {
            this.showError('Vui lòng nhập họ và tên');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        if (!formData.email) {
            this.showError('Vui lòng nhập email');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        // Email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(formData.email)) {
            this.showError('Email không hợp lệ');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        try {
            // Get access token from localStorage
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                this.showError('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
                this.resetButton(submitBtn, originalText);
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
                return;
            }
            
            const response = await fetch('/api/users/me', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                this.showSuccess('Cập nhật thông tin thành công!');
                
                // Close modal and reload page
                const modal = bootstrap.Modal.getInstance(document.getElementById('editProfileModal'));
                modal.hide();
                
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Có lỗi xảy ra khi cập nhật thông tin');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            this.showError('Không thể kết nối đến server');
        }
        
        this.resetButton(submitBtn, originalText);
    }

    async handleChangePassword(e) {
        e.preventDefault();
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Đang đổi...';
        
        const oldPassword = document.getElementById('oldPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // Client-side validation
        if (!oldPassword) {
            this.showError('Vui lòng nhập mật khẩu hiện tại');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        if (!newPassword) {
            this.showError('Vui lòng nhập mật khẩu mới');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        if (newPassword.length < 6) {
            this.showError('Mật khẩu phải có ít nhất 6 ký tự');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        if (newPassword !== confirmPassword) {
            this.showError('Mật khẩu xác nhận không khớp');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        if (oldPassword === newPassword) {
            this.showError('Mật khẩu mới phải khác mật khẩu hiện tại');
            this.resetButton(submitBtn, originalText);
            return;
        }
        
        const formData = {
            old_password: oldPassword,
            new_password: newPassword
        };
        
        try {
            // Get access token from localStorage
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                this.showError('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
                this.resetButton(submitBtn, originalText);
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
                return;
            }
            
            const response = await fetch('/api/users/me/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                this.showSuccess('Đổi mật khẩu thành công!');
                
                // Close modal and clear form
                const modal = bootstrap.Modal.getInstance(document.getElementById('changePasswordModal'));
                modal.hide();
                document.getElementById('changePasswordForm').reset();
                
                // Reset password visibility
                ['oldPassword', 'newPassword', 'confirmPassword'].forEach(id => {
                    const input = document.getElementById(id);
                    const icon = input.nextElementSibling.querySelector('i');
                    input.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                });
            } else {
                const error = await response.json();
                this.showError(error.detail || 'Có lỗi xảy ra khi đổi mật khẩu');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            this.showError('Không thể kết nối đến server');
        }
        
        this.resetButton(submitBtn, originalText);
    }

    handleKeyboardShortcuts(e) {
        if (e.key === 'Escape') {
            const editModal = bootstrap.Modal.getInstance(document.getElementById('editProfileModal'));
            const passwordModal = bootstrap.Modal.getInstance(document.getElementById('changePasswordModal'));
            
            if (editModal) editModal.hide();
            if (passwordModal) passwordModal.hide();
        }
    }

    resetButton(button, originalText) {
        button.disabled = false;
        button.innerHTML = originalText;
    }

    showSuccess(message) {
        if (window.NotificationManager) {
            NotificationManager.showSuccess(message);
        } else {
            alert(message);
        }
    }

    showError(message) {
        if (window.NotificationManager) {
            NotificationManager.showError(message);
        } else {
            alert(message);
        }
    }
}

// Global functions for template access
function openEditProfileModal() {
    if (window.profileManager) {
        window.profileManager.openEditProfileModal();
    }
}

function openChangePasswordModal() {
    if (window.profileManager) {
        window.profileManager.openChangePasswordModal();
    }
}

function togglePassword(inputId) {
    if (window.profileManager) {
        window.profileManager.togglePassword(inputId);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.profileManager = new ProfileManager();
});

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProfileManager;
}
