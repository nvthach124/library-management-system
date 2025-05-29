/**
 * Admin Borrows Management JavaScript
 * Handles the functionality for managing borrow orders in the admin panel
 */

// Utility function to get access token from cookie
window.getAccessToken = () => {
    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    };
    return getCookie('access_token');
};

document.addEventListener('DOMContentLoaded', function() {
    
    // Elements
    const ordersTableBody = document.getElementById('orders-table-body');
    const statusFilter = document.getElementById('status-filter');
    const searchInput = document.getElementById('search-input');
    const refreshBtn = document.getElementById('refresh-btn');
    const pagination = document.getElementById('pagination');
    
    // Stats elements
    const pendingCount = document.getElementById('pending-count');
    const activeCount = document.getElementById('active-count');
    const overdueCount = document.getElementById('overdue-count');
    const completedCount = document.getElementById('completed-count');
    
    // Order detail modal elements
    const orderDetailModal = new bootstrap.Modal(document.getElementById('orderDetailModal'));
    const returnBookModal = new bootstrap.Modal(document.getElementById('returnBookModal'));
    
    // Current page and filter state
    let currentPage = 1;
    let currentStatus = '';
    let currentSearch = '';
    let currentLimit = 10;
    
    // Load orders and stats on page load
    loadOrders();
    loadStats();
    
    // Event listeners
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadOrders();
            loadStats();
        });
    }
    
    // Add event delegation for return-books buttons
    document.addEventListener('click', function(e) {
        if (e.target.closest('.return-books')) {
            const orderId = e.target.closest('.return-books').dataset.id;
            returnBooksFromList(orderId);
        }
    });
    
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            currentStatus = this.value;
            currentPage = 1;
            loadOrders();
        });
    }
    
    if (searchInput) {
        // Add debounce to search
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentSearch = this.value;
                currentPage = 1;
                loadOrders();
            }, 500);
        });
    }
    
    /**
     * Load orders with pagination and filters
     */
    function loadOrders() {
        // Show loading state
        ordersTableBody.innerHTML = '<tr><td colspan="7" class="text-center py-3"><i class="fas fa-spinner fa-spin me-2"></i>Đang tải dữ liệu...</td></tr>';
        
        // Build query parameters
        let params = new URLSearchParams({
            page: currentPage,
            limit: currentLimit
        });
        
        if (currentStatus) {
            params.append('status', currentStatus);
        }
        
        if (currentSearch) {
            params.append('search', currentSearch);
        }
        
        // Fetch orders from API
        fetch(`/api/borrow-orders/admin?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.getAccessToken()}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Không thể tải danh sách đơn mượn');
            }
            return response.json();
        })
        .then(data => {
            renderOrders(data.items);
            renderPagination(data.page, data.pages, data.total);
        })
        .catch(error => {
            ordersTableBody.innerHTML = `<tr><td colspan="7" class="text-center py-3 text-danger"><i class="fas fa-exclamation-circle me-2"></i>${error.message}</td></tr>`;
        });
    }
    
    /**
     * Load order statistics
     */
    function loadStats() {
        fetch('/api/borrow-orders/admin/stats', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.getAccessToken()}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Không thể tải thống kê đơn mượn');
            }
            return response.json();
        })
        .then(data => {
            // Update stats counters
            if (pendingCount) pendingCount.textContent = data.pending;
            if (activeCount) activeCount.textContent = data.active;
            if (overdueCount) overdueCount.textContent = data.overdue;
            if (completedCount) completedCount.textContent = data.completed;
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
    }
    
    /**
     * Render orders to the table
     */
    function renderOrders(orders) {
        if (!orders || orders.length === 0) {
            ordersTableBody.innerHTML = '<tr><td colspan="7" class="text-center py-3">Không có đơn mượn nào</td></tr>';
            return;
        }
        
        let html = '';
        
        orders.forEach(order => {
            const statusClass = getStatusClass(order.status);
            const statusText = getStatusText(order.status);
            
            html += `
            <tr>
                <td>
                    <div class="d-flex px-2 py-1">
                        <div class="d-flex flex-column justify-content-center">
                            <h6 class="mb-0 text-sm">#${order.id}</h6>
                        </div>
                    </div>
                </td>
                <td>
                    <p class="text-xs font-weight-bold mb-0">${order.user.full_name}</p>
                    <p class="text-xs text-secondary mb-0">${order.user.email}</p>
                </td>
                <td>
                    <p class="text-xs font-weight-bold mb-0">${formatDate(order.order_date)}</p>
                </td>
                <td>
                    <p class="text-xs font-weight-bold mb-0">${formatDate(order.due_date)}</p>
                </td>
                <td>
                    <span class="badge badge-sm ${statusClass}">${statusText}</span>
                </td>
                <td>
                    <p class="text-xs font-weight-bold mb-0">${order.books.length}</p>
                </td>
                <td>
                    <button class="btn btn-link text-secondary mb-0" onclick="viewOrderDetail(${order.id})">
                        <i class="fas fa-eye text-xs"></i> Xem
                    </button>
                </td>
            </tr>
            `;
        });
        
        ordersTableBody.innerHTML = html;
    }
    
    /**
     * Render pagination controls
     */
    function renderPagination(page, pages, total) {
        if (!pagination) return;
        
        if (pages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
        let html = '';
        
        // Previous button
        html += `
        <li class="page-item ${page === 1 ? 'disabled' : ''}">
            <a class="page-link" href="javascript:;" onclick="changePage(${page - 1})" aria-label="Previous">
                <span aria-hidden="true">&laquo;</span>
            </a>
        </li>
        `;
        
        // Page numbers
        const startPage = Math.max(1, page - 2);
        const endPage = Math.min(pages, page + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            html += `
            <li class="page-item ${i === page ? 'active' : ''}">
                <a class="page-link" href="javascript:;" onclick="changePage(${i})">${i}</a>
            </li>
            `;
        }
        
        // Next button
        html += `
        <li class="page-item ${page === pages ? 'disabled' : ''}">
            <a class="page-link" href="javascript:;" onclick="changePage(${page + 1})" aria-label="Next">
                <span aria-hidden="true">&raquo;</span>
            </a>
        </li>
        `;
        
        pagination.innerHTML = html;
    }
    
    /**
     * Change current page
     */
    window.changePage = function(page) {
        if (page < 1) return;
        
        currentPage = page;
        loadOrders();
        
        // Scroll to top of table
        document.querySelector('.card').scrollIntoView({ behavior: 'smooth' });
    };
    
    /**
     * View order details
     */
    window.viewOrderDetail = function(orderId) {
        fetch(`/api/borrow-orders/admin/${orderId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.getAccessToken()}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Không thể tải thông tin đơn mượn');
            }
            return response.json();
        })
        .then(order => {
            // Set order details in modal
            document.getElementById('order-id').textContent = `#${order.id}`;
            document.getElementById('order-user').textContent = order.user.full_name;
            document.getElementById('order-email').textContent = order.user.email;
            document.getElementById('order-date').textContent = formatDate(order.order_date);
            document.getElementById('order-due-date').textContent = formatDate(order.due_date);
            document.getElementById('order-status').textContent = getStatusText(order.status);
            document.getElementById('order-status').className = `badge ${getStatusClass(order.status)}`;
            document.getElementById('order-notes').textContent = order.notes || 'Không có';
            
            // Render books and action buttons
            renderOrderBooks(order);
            renderOrderActions(order);
            
            // Show the modal
            orderDetailModal.show();
        })
        .catch(error => {
            alert(`Lỗi: ${error.message}`);
        });
    };
    
    /**
     * Render books in the order detail modal
     */
    function renderOrderBooks(order) {
        const orderBooks = document.getElementById('order-books');
        if (!orderBooks) return;
        
        let html = '';
        
        order.books.forEach(book => {
            // Find borrow record for this book if it exists
            const borrow = order.borrows ? order.borrows.find(b => b.book_id === book.id) : null;
            const isReturned = borrow && borrow.is_returned;
            const borrowId = borrow ? borrow.id : null;
            const bookTitle = book.title.replace(/'/g, "\\'");
            const userName = order.user.full_name.replace(/'/g, "\\'");
            const borrowDate = borrow ? formatDate(borrow.borrow_date) : '';
            const dueDate = borrow ? formatDate(borrow.due_date) : '';
            
            html += `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <img src="${book.cover_image || '/static/images/book_default.svg'}" class="avatar avatar-sm me-3" alt="${book.title}">
                        <div class="d-flex flex-column">
                            <h6 class="mb-0 text-sm">${book.title}</h6>
                        </div>
                    </div>
                </td>
                <td>${book.author_name}</td>
                <td>
                    ${isReturned ? 
                        '<span class="badge badge-sm bg-gradient-success">Đã trả</span>' : 
                        '<span class="badge badge-sm bg-gradient-info">Đang mượn</span>'}
                </td>
                <td>
                    ${!isReturned && order.status === 'active' ? 
                        `<button class="btn btn-sm btn-primary" onclick="openReturnModal(${borrowId}, '${bookTitle}', '${userName}', '${borrowDate}', '${dueDate}')">Ghi nhận trả</button>` : 
                        ''}
                </td>
            </tr>
            `;
        });
        
        orderBooks.innerHTML = html;
    }
    
    /**
     * Render action buttons for the order
     */
    function renderOrderActions(order) {
        const actionsContainer = document.getElementById('order-actions');
        if (!actionsContainer) return;
        
        let html = '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Đóng</button>';
        
        if (order.status === 'pending') {
            html += `
            <button type="button" class="btn btn-success approve-order" data-id="${order.id}" onclick="approveOrder(${order.id})">
                <i class="fas fa-check me-1"></i> Duyệt đơn
            </button>
            <button type="button" class="btn btn-danger reject-order" data-id="${order.id}" onclick="rejectOrder(${order.id})">
                <i class="fas fa-times me-1"></i> Từ chối
            </button>
            `;
        } else if (order.status === 'active' || order.status === 'overdue') {
            // Check if all books are returned
            const allReturned = order.borrows && order.borrows.every(b => b.is_returned);
            
            if (allReturned) {
                html += `
                <button type="button" class="btn btn-success complete-order" data-id="${order.id}" onclick="completeOrder(${order.id})">
                    <i class="fas fa-check-circle me-1"></i> Hoàn thành đơn
                </button>
                `;
            }
        }
        
        actionsContainer.innerHTML = html;
    }

/**
     * Complete an order
     */
    window.completeOrder = function(orderId) {
            Swal.fire({
            title: 'Xác nhận hoàn thành',
            text: 'Bạn có chắc chắn muốn đánh dấu đơn mượn này là đã hoàn thành?',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Xác nhận',
            cancelButtonText: 'Hủy'
        }).then((result) => {
            if (!result.isConfirmed) {
                return;
            }
            
            // Show loading state on the complete button in the modal
            const completeBtn = document.querySelector(`.complete-order[data-id="${orderId}"]`);
            if (completeBtn) {
                completeBtn.disabled = true;
                completeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Đang xử lý...';
            }
            
            fetch(`/api/borrow-orders/admin/${orderId}/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${window.getAccessToken()}`
                },
                credentials: 'same-origin'
            })
            .then(response => {
                if (response.ok) {
                    return response.json().then(data => {
                        handleCompletionSuccess(data, orderId);
                    });
                } else if (response.status === 400) {
                    // Có thể còn sách chưa trả
                    return response.json().then(error => {
                        // Hiển thị xác nhận trả tất cả sách và hoàn thành đơn
                Swal.fire({
                            title: 'Sách chưa trả',
                            html: `<p>${error.detail}</p><p>Bạn có muốn đánh dấu tất cả sách là đã trả và hoàn thành đơn không?</p>`,
                            icon: 'warning',
                            showCancelButton: true,
                            confirmButtonText: 'Đánh dấu tất cả đã trả',
                            cancelButtonText: 'Hủy'
                        }).then((result) => {
                            if (result.isConfirmed) {
                                // Gọi API đánh dấu tất cả sách là đã trả và hoàn thành đơn
                                completeOrderWithReturns(orderId);
                            } else {
                // Reset button state if it exists
                                if (completeBtn) {
                                    completeBtn.disabled = false;
                                    completeBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Hoàn thành đơn';
                                }
                            }
                });
            });
                        } else {
                    throw new Error('Không thể hoàn thành đơn mượn');
                }
            })
            .catch(error => {
                // Reset button state if it exists
                if (completeBtn) {
                    completeBtn.disabled = false;
                    completeBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Hoàn thành đơn';
                }
                
                Swal.fire({
                    title: 'Lỗi!',
                    text: error.message,
                    icon: 'error',
                    confirmButtonText: 'Đóng'
                });
            });
        });
    };
    
    function completeOrderWithReturns(orderId) {
        // Show loading
                Swal.fire({
                    title: 'Đang xử lý',
            text: 'Đang đánh dấu tất cả sách là đã trả...',
                    allowOutsideClick: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });
                
        fetch(`/api/borrow-orders/admin/${orderId}/complete-with-returns`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': `Bearer ${window.getAccessToken()}`
                                },
                                credentials: 'same-origin'
        })
        .then(response => {
                            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.detail || 'Không thể hoàn thành đơn mượn');
                });
            }
            return response.json();
        })
        .then(data => {
            handleCompletionSuccess(data, orderId);
        })
        .catch(error => {
            // Show error message
            Swal.fire({
                title: 'Lỗi!',
                text: error.message,
                icon: 'error',
                confirmButtonText: 'Đóng'
            });
            
            // Reset button state
            const completeBtn = document.querySelector(`.complete-order[data-id="${orderId}"]`);
            if (completeBtn) {
                completeBtn.disabled = false;
                completeBtn.innerHTML = '<i class="fas fa-check-circle me-1"></i> Hoàn thành đơn';
            }
        });
    }
    
    function handleCompletionSuccess(data, orderId) {
                // Show success message
        let message = data.message;
        if (data.returned_books) {
            message = `Đã hoàn thành đơn mượn và đánh dấu ${data.returned_books} sách là đã trả!`;
        }
        
                Swal.fire({
                    title: 'Thành công!',
            text: message,
                    icon: 'success',
                    confirmButtonText: 'Đóng'
                });
                
                // Reload orders and stats
                loadOrders();
                loadStats();
                
                // Close the modal
        if (orderDetailModal && typeof orderDetailModal.hide === 'function') {
                orderDetailModal.hide();
        }
    }
    
    /**
     * Helper function to format date
     */
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    }
    
    /**
     * Get status class for badge
     */
    function getStatusClass(status) {
        switch (status) {
            case 'pending':
                return 'bg-warning';
            case 'active':
                return 'bg-info';
            case 'overdue':
                return 'bg-danger';
            case 'completed':
                return 'bg-success';
            case 'cancelled':
                return 'bg-secondary';
            case 'rejected':
                return 'bg-dark';
            default:
                return 'bg-secondary';
        }
    }
    
    /**
     * Get status text
     */
    function getStatusText(status) {
        switch (status) {
            case 'pending':
                return 'Chờ duyệt';
            case 'active':
                return 'Đang mượn';
            case 'overdue':
                return 'Quá hạn';
            case 'completed':
                return 'Hoàn thành';
            case 'cancelled':
                return 'Đã hủy';
            case 'rejected':
                return 'Từ chối';
            default:
                return status;
        }
    }
});