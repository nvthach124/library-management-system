/**
 * Notification system for the Library Management System
 * Handles loading, displaying, and managing notifications in the UI
 */

class NotificationManager {
    constructor() {
        this.notificationBtn = document.getElementById('notification-btn');
        this.notificationDropdown = document.getElementById('notification-dropdown');
        this.notificationsList = document.getElementById('notifications-list');
        this.notificationCount = document.getElementById('notification-count');
        this.markAllReadBtn = document.getElementById('mark-all-read-btn');
        
        this.isDropdownOpen = false;
        this.notifications = [];
        this.unreadCount = 0;
        
        this.init();
    }
    
    init() {
        if (!this.notificationBtn) return;
        
        // Bind event listeners
        this.notificationBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });
        
        if (this.markAllReadBtn) {
            this.markAllReadBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.notificationDropdown?.contains(e.target)) {
                this.closeDropdown();
            }
        });
        
        // Load notifications on page load
        this.loadNotifications();
        
        // Refresh notifications periodically
        setInterval(() => {
            this.loadNotifications();
        }, 60000); // Every minute
    }
    
    async loadNotifications() {
        try {
            // Get access token
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                this.hideNotificationElements();
                return;
            }
            
            // Set up headers with auth token
            const headers = {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            };
            
            // Get unread count first
            const unreadResponse = await fetch('/api/notifications/unread-count', { headers });
            if (unreadResponse.ok) {
                const unreadData = await unreadResponse.json();
                this.updateNotificationCount(unreadData.count);
            }
            
            // Get notifications (only unread for dropdown)
            const response = await fetch('/api/notifications/?unread_only=true', { headers });
            if (!response.ok) {
                if (response.status === 401) {
                    // User not logged in, hide notification elements
                    this.hideNotificationElements();
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }
            
            const notifications = await response.json();
            this.notifications = notifications;
            this.updateDropdownContent();
            
        } catch (error) {
            console.error('Error loading notifications:', error);
            if (error.message.includes('401')) {
                this.hideNotificationElements();
            }
        }
    }
    
    hideNotificationElements() {
        if (this.notificationBtn) {
            this.notificationBtn.style.display = 'none';
        }
    }
    
    updateNotificationCount(count) {
        this.unreadCount = count;
        
        if (this.notificationCount) {
            this.notificationCount.textContent = count;
            this.notificationCount.style.display = count > 0 ? 'inline' : 'none';
        }
        
        // Update page title with notification count
        if (count > 0) {
            document.title = `(${count}) Thư Viện`;
        } else {
            document.title = 'Thư Viện';
        }
    }
    
    updateDropdownContent() {
        if (!this.notificationsList) return;
        
        if (this.notifications.length === 0) {
            this.notificationsList.innerHTML = `
                <div class="no-notifications">
                    <i class="fas fa-bell-slash"></i>
                    <p>Không có thông báo mới</p>
                </div>
            `;
            return;
        }
        
        const notificationsHtml = this.notifications.map(notification => 
            this.createNotificationHTML(notification)
        ).join('');
        
        this.notificationsList.innerHTML = notificationsHtml;
        
        // Add click handlers for individual notifications
        this.notificationsList.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const notificationId = item.dataset.notificationId;
                this.markAsRead(notificationId);
            });
        });
    }
    
    createNotificationHTML(notification) {
        const timeAgo = this.formatTimeAgo(new Date(notification.created_at));
        const typeIcon = this.getNotificationIcon(notification.type);
        
        return `
            <div class="notification-item ${!notification.is_read ? 'unread' : ''}" 
                 data-notification-id="${notification.id}">
                <div class="notification-icon ${notification.type}">
                    <i class="${typeIcon}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${timeAgo}</div>
                </div>
                ${!notification.is_read ? '<div class="unread-indicator"></div>' : ''}
            </div>
        `;
    }
    
    getNotificationIcon(type) {
        const icons = {
            'success': 'fas fa-check-circle',
            'warning': 'fas fa-exclamation-triangle',
            'danger': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        };
        return icons[type] || 'fas fa-bell';
    }
    
    formatTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) {
            return 'Vừa xong';
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes} phút trước`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours} giờ trước`;
        } else {
            const days = Math.floor(diffInSeconds / 86400);
            return `${days} ngày trước`;
        }
    }
    
    toggleDropdown() {
        if (this.isDropdownOpen) {
            this.closeDropdown();
        } else {
            this.openDropdown();
        }
    }
    
    openDropdown() {
        if (!this.notificationDropdown) return;
        
        this.notificationDropdown.classList.add('show');
        this.isDropdownOpen = true;
        
        // Load fresh notifications when opening
        this.loadNotifications();
    }
    
    closeDropdown() {
        if (!this.notificationDropdown) return;
        
        this.notificationDropdown.classList.remove('show');
        this.isDropdownOpen = false;
    }
    
    async markAsRead(notificationId) {
        try {
            // Get access token
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                this.showToast('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
                return;
            }
            
            const response = await fetch(`/api/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                }
            });
            
            if (response.ok) {
                // Update local state
                const notification = this.notifications.find(n => n.id == notificationId);
                if (notification) {
                    notification.is_read = true;
                }
                
                // Refresh the display
                this.loadNotifications();
                this.showToast('Đã đánh dấu thông báo là đã đọc', 'success');
            }
        } catch (error) {
            console.error('Error marking notification as read:', error);
            this.showToast('Có lỗi xảy ra khi đánh dấu thông báo', 'error');
        }
    }
    
    async markAllAsRead() {
        try {
            // Get access token
            const accessToken = localStorage.getItem('access_token');
            if (!accessToken) {
                this.showToast('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.', 'error');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
                return;
            }
            
            const response = await fetch('/api/notifications/read-all', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                }
            });
            
            if (response.ok) {
                // Update local state
                this.notifications.forEach(notification => {
                    notification.is_read = true;
                });
                
                // Refresh the display
                this.loadNotifications();
                this.showToast('Đã đánh dấu tất cả thông báo là đã đọc', 'success');
            }
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
            this.showToast('Có lỗi xảy ra khi đánh dấu thông báo', 'error');
        }
    }
    
    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(toast);
        
        // Show toast
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Hide and remove toast
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    }
}

// Initialize notification manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new NotificationManager();
});