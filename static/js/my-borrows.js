document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const pendingTab = document.getElementById('pending-tab');
    const activeTab = document.getElementById('active-tab');
    const completedTab = document.getElementById('completed-tab');
    const pendingContainer = document.getElementById('pending-orders');
    const activeContainer = document.getElementById('active-orders');
    const completedContainer = document.getElementById('completed-orders');
    
    // State
    let selectedTab = 'active';
    let pendingOrders = [];
    let activeOrders = [];
    let completedOrders = [];
    
    // Initialize
    loadOrders();
    
    // Event listeners
    if (pendingTab) {
        pendingTab.addEventListener('click', function() {
            showTab('pending');
        });
    }
    
    if (activeTab) {
        activeTab.addEventListener('click', function() {
            showTab('active');
        });
    }
    
    if (completedTab) {
        completedTab.addEventListener('click', function() {
            showTab('completed');
        });
    }
    
    // Attach event listener for cancel buttons
    if (pendingContainer) {
        pendingContainer.addEventListener('click', function(e) {
            const cancelBtn = e.target.closest('.cancel-order');
            if (cancelBtn) {
                e.preventDefault();
                const orderId = parseInt(cancelBtn.getAttribute('data-id'));
                cancelOrder(orderId);
            }
        });
    }
    
    // Attach event listener for return buttons
    if (activeContainer) {
        activeContainer.addEventListener('click', function(e) {
            const returnBookBtn = e.target.closest('.return-book');
            if (returnBookBtn) {
                e.preventDefault();
                const borrowId = parseInt(returnBookBtn.getAttribute('data-id'));
                const bookTitle = returnBookBtn.getAttribute('data-title');
                returnBook(borrowId, bookTitle);
            }
        });
    }
    
    // Functions
    function showTab(tabName) {
        selectedTab = tabName;
        
        // Update active tab
        pendingTab.classList.remove('active');
        activeTab.classList.remove('active');
        completedTab.classList.remove('active');
        
        // Hide all containers
        pendingContainer.style.display = 'none';
        activeContainer.style.display = 'none';
        completedContainer.style.display = 'none';
        
        // Show selected tab and container
        if (tabName === 'pending') {
            pendingTab.classList.add('active');
            pendingContainer.style.display = 'block';
        } else if (tabName === 'active') {
            activeTab.classList.add('active');
            activeContainer.style.display = 'block';
        } else if (tabName === 'completed') {
            completedTab.classList.add('active');
            completedContainer.style.display = 'block';
        }
    }
    
    function loadOrders() {
        // Show loading
        pendingContainer.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
        activeContainer.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
        completedContainer.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Đang tải...</div>';
        
        // Get the current hostname and port
        const baseUrl = window.location.protocol + '//' + window.location.host;
        
        // Fetch orders from API
        fetch(`${baseUrl}/api/borrow-orders/my-orders`, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Không thể tải danh sách đơn mượn');
            }
            return response.json();
        })
        .then(orders => {
            // Split orders by status
            pendingOrders = orders.filter(order => order.status === 'pending');
            activeOrders = orders.filter(order => ['active', 'overdue'].includes(order.status));
            completedOrders = orders.filter(order => ['completed', 'cancelled', 'rejected'].includes(order.status));
            
            // Render orders
            renderOrders();
            
            // Show current tab
            showTab(selectedTab);
            
            // Update badges
            updateTabBadges();

            // Process active orders directly
            activeOrders.forEach(order => {
                if (order.books && order.books.length > 0) {
                    // Create a borrows array with default "not returned" status for each book
                    order.borrows = order.books.map(book => ({
                        id: order.id + "_" + book.id, // Create a unique ID
                        book_id: book.id,
                        order_id: order.id,
                        is_returned: false // Default to not returned
                    }));
                }
            });

            // Re-render active orders
            renderActiveOrders();
        })
        .catch(error => {
            console.error('Error:', error);
            pendingContainer.innerHTML = '<div class="error">Có lỗi xảy ra khi tải danh sách đơn mượn</div>';
            activeContainer.innerHTML = '<div class="error">Có lỗi xảy ra khi tải danh sách đơn mượn</div>';
            completedContainer.innerHTML = '<div class="error">Có lỗi xảy ra khi tải danh sách đơn mượn</div>';
        });
    }
    
    function renderOrders() {
        renderPendingOrders();
        renderActiveOrders();
        renderCompletedOrders();
    }
    
    function renderPendingOrders() {
        if (pendingOrders.length === 0) {
            pendingContainer.innerHTML = '<div class="empty-state">Bạn không có đơn mượn nào đang chờ duyệt</div>';
            return;
        }
        
        let html = '';
        pendingOrders.forEach(order => {
            html += `
                <div class="order-card pending">
                    <div class="order-header">
                        <div class="order-info">
                            <h3 class="order-id">Đơn mượn #${order.id}</h3>
                            <span class="order-date">Ngày tạo: ${formatDate(order.order_date)}</span>
                        </div>
                        <span class="order-status status-pending">Chờ duyệt</span>
                    </div>
                    
                    <div class="order-books">
                        ${renderBooksList(order.books)}
                    </div>
                    
                    <div class="order-actions">
                        <button class="btn btn-danger cancel-order" data-id="${order.id}">
                            <i class="fas fa-times"></i> Hủy đơn
                        </button>
                    </div>
                </div>
            `;
        });
        
        pendingContainer.innerHTML = html;
    }
    
    function renderActiveOrders() {
        if (activeOrders.length === 0) {
            activeContainer.innerHTML = '<div class="empty-state">Bạn không có sách nào đang mượn</div>';
            return;
        }
        
        let html = '';
        activeOrders.forEach(order => {
            const isOverdue = order.status === 'overdue';
            const daysLeft = getDaysLeft(order.due_date);
            const dueText = isOverdue 
                ? `<span class="overdue">Quá hạn ${Math.abs(daysLeft)} ngày</span>` 
                : `<span class="due-date ${daysLeft <= 3 ? 'due-soon' : ''}">Còn ${daysLeft} ngày</span>`;
            
            html += `
                <div class="order-card ${isOverdue ? 'overdue' : 'active'}">
                    <div class="order-header">
                        <div class="order-info">
                            <h3 class="order-id">Đơn mượn #${order.id}</h3>
                            <span class="order-date">Ngày mượn: ${formatDate(order.order_date)}</span>
                            <span class="order-due">Hạn trả: ${formatDate(order.due_date)} ${dueText}</span>
                        </div>
                        <span class="order-status status-${isOverdue ? 'overdue' : 'active'}">${isOverdue ? 'Quá hạn' : 'Đang mượn'}</span>
                    </div>
                    
                    <div class="order-books">
                        ${renderBorrowedBooksList(order.books, order.borrows)}
                    </div>
                </div>
            `;
        });
        
        activeContainer.innerHTML = html;
    }
    
    function renderCompletedOrders() {
        if (completedOrders.length === 0) {
            completedContainer.innerHTML = '<div class="empty-state">Bạn chưa có đơn mượn nào đã hoàn thành</div>';
            return;
        }
        
        let html = '';
        completedOrders.forEach(order => {
            let statusClass = '';
            let statusText = '';
            
            if (order.status === 'completed') {
                statusClass = 'status-completed';
                statusText = 'Đã trả';
            } else if (order.status === 'cancelled') {
                statusClass = 'status-cancelled';
                statusText = 'Đã hủy';
            } else if (order.status === 'rejected') {
                statusClass = 'status-rejected';
                statusText = 'Bị từ chối';
            }
            
            html += `
                <div class="order-card completed">
                    <div class="order-header">
                        <div class="order-info">
                            <h3 class="order-id">Đơn mượn #${order.id}</h3>
                            <span class="order-date">Ngày mượn: ${formatDate(order.order_date)}</span>
                            <span class="order-date">Hạn trả: ${formatDate(order.due_date)}</span>
                        </div>
                        <span class="order-status ${statusClass}">${statusText}</span>
                    </div>
                    
                    <div class="order-books">
                        ${renderBooksList(order.books)}
                    </div>
                </div>
            `;
        });
        
        completedContainer.innerHTML = html;
    }
    
    function renderBooksList(books) {
        let html = '';
        books.forEach(book => {
            html += `
                <div class="book-item">
                    <div class="book-image">
                        <img src="${book.cover_image || '/static/images/book_default.svg'}" alt="${book.title}">
                    </div>
                    <div class="book-info">
                        <h4 class="book-title">${book.title}</h4>
                        <p class="book-author">${book.author_name}</p>
                    </div>
                </div>
            `;
        });
        return html;
    }
    
    function renderBorrowedBooksList(books, borrows) {
        if (!borrows) return renderBooksList(books);
        
        let html = '';
        books.forEach(book => {
            // Find borrow record for this book
            const borrow = borrows.find(b => b.book_id === book.id);
            const isReturned = borrow && borrow.is_returned;
            
            html += `
                <div class="book-item ${isReturned ? 'returned' : ''}">
                    <div class="book-image">
                        <img src="${book.cover_image || '/static/images/book_default.svg'}" alt="${book.title}">
                    </div>
                    <div class="book-info">
                        <h4 class="book-title">${book.title}</h4>
                        <p class="book-author">${book.author_name}</p>
                        ${isReturned ? '<span class="returned-badge">Đã trả</span>' : ''}
                    </div>
                    ${!isReturned && borrow ? `
                    <div class="book-actions">
                        <button class="btn btn-primary return-book" data-id="${borrow.id}" data-title="${book.title}">
                            <i class="fas fa-undo"></i> Trả sách
                        </button>
                    </div>
                    ` : ''}
                </div>
            `;
        });
        return html;
    }
    
    function updateTabBadges() {
        const pendingCount = pendingOrders.length;
        const activeCount = activeOrders.length;
        const completedCount = completedOrders.length;
        
        if (pendingCount > 0) {
            pendingTab.querySelector('.badge').textContent = pendingCount;
            pendingTab.querySelector('.badge').style.display = 'inline-block';
        } else {
            pendingTab.querySelector('.badge').style.display = 'none';
        }
        
        if (activeCount > 0) {
            activeTab.querySelector('.badge').textContent = activeCount;
            activeTab.querySelector('.badge').style.display = 'inline-block';
        } else {
            activeTab.querySelector('.badge').style.display = 'none';
        }
        
        if (completedCount > 0) {
            completedTab.querySelector('.badge').textContent = completedCount;
            completedTab.querySelector('.badge').style.display = 'inline-block';
        } else {
            completedTab.querySelector('.badge').style.display = 'none';
        }
    }
    
    function cancelOrder(orderId) {
        if (!confirm('Bạn có chắc chắn muốn hủy đơn mượn này?')) {
            return;
        }
        
        // Get the current hostname and port
        const baseUrl = window.location.protocol + '//' + window.location.host;
        
        fetch(`${baseUrl}/api/borrow-orders/${orderId}/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Không thể hủy đơn mượn');
            }
            return response.json();
        })
        .then(result => {
            showToast(result.message, 'success');
            
            // Update orders
            const order = pendingOrders.find(o => o.id === orderId);
            if (order) {
                order.status = 'cancelled';
                pendingOrders = pendingOrders.filter(o => o.id !== orderId);
                completedOrders.push(order);
                
                // Re-render
                renderOrders();
                updateTabBadges();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(error.message, 'error');
        });
    }
    
    function returnBook(borrowId, bookTitle) {
        if (!confirm(`Bạn có chắc chắn muốn trả sách "${bookTitle}"?`)) {
            return;
        }
        
        // Get the current hostname and port
        const baseUrl = window.location.protocol + '//' + window.location.host;
        
        fetch(`${baseUrl}/api/books/return/${borrowId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAccessToken()}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Không thể trả sách');
            }
            return response.json();
        })
        .then(result => {
            showToast(result.message, 'success');
            
            // Reload orders
            loadOrders();
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(error.message, 'error');
        });
    }
    
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('vi-VN');
    }
    
    function getDaysLeft(dueDate) {
        const due = new Date(dueDate);
        const now = new Date();
        
        // Reset time to compare dates only
        due.setHours(0, 0, 0, 0);
        now.setHours(0, 0, 0, 0);
        
        const diffTime = due - now;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        return diffDays;
    }
    
    function showToast(message, type) {
        // Use SweetAlert for toasts if available
        if (typeof Swal !== 'undefined') {
            const Toast = Swal.mixin({
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            
            Toast.fire({
                icon: type,
                title: message
            });
        } else {
            alert(message);
        }
    }
    
    // Utility function to get access token from cookie
    function getAccessToken() {
        const getCookie = (name) => {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };
        return getCookie('access_token');
    }
});
