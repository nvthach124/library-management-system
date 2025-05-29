/**
 * Cart functionality for the library system
 * This script handles adding books to the cart and persisting it across pages
 * Combined functionality from cart.js and cart-sync.js
 */

// Global cart management class
class CartManager {
    constructor() {
        this.cart = [];
        this.borrowedBooks = []; // Danh sách sách đang mượn
        this.pendingBooks = []; // Danh sách sách đang chờ duyệt
        this.eventListeners = [];
        this.init();
    }

    init() {
        // Load cart from localStorage
        this.loadCart();
        
        // Listen for storage changes (from other tabs/windows)
        window.addEventListener('storage', (e) => {
            if (e.key === 'borrowCart') {
                this.loadCart();
                this.updateAllButtons();
                
                // Update cart UI if it exists on the page
                if (typeof updateCartUI === 'function') {
                    updateCartUI();
                }
                
                this.notifyListeners();
            }
        });

        // Listen for focus events to sync when returning to tab
        window.addEventListener('focus', () => {
            this.syncCart();
        });

        // Listen for pageshow events (back/forward navigation)
        window.addEventListener('pageshow', () => {
            this.syncCart();
        });

        // Listen for custom cart change events (same window)
        window.addEventListener('cartChanged', (e) => {
            const { cart, specificBookId } = e.detail;
            this.cart = cart;
            if (specificBookId) {
                this.updateBookButton(specificBookId);
            } else {
                this.updateAllButtons();
            }
            
            // Update cart UI if it exists on the page
            if (typeof updateCartUI === 'function') {
                updateCartUI();
            }
        });

        // Initial button sync
        setTimeout(() => {
            this.loadBorrowedBooks(); // Load borrowed books first
            this.loadPendingBooks(); // Load pending books
            this.updateAllButtons();
            
            // Also update cart UI if it exists on the page
            if (typeof updateCartUI === 'function') {
                updateCartUI();
            }
        }, 100);
    }

    loadCart() {
        try {
            const cartData = localStorage.getItem('borrowCart');
            this.cart = cartData ? JSON.parse(cartData) : [];
        } catch (error) {
            console.error('Error loading cart:', error);
            this.cart = [];
        }
    }

    saveCart(specificBookId = null) {
        try {
            localStorage.setItem('borrowCart', JSON.stringify(this.cart));
            
            // Broadcast change to other tabs/windows
            this.broadcastCartChange(specificBookId);
            
            // Chỉ cập nhật nút của sách cụ thể nếu được chỉ định
            if (specificBookId) {
                this.updateBookButton(specificBookId);
            } else {
                this.updateAllButtons();
            }
            
            // Update cart UI if it exists on the page
            if (typeof updateCartUI === 'function') {
                updateCartUI();
            }
            
            this.notifyListeners();
        } catch (error) {
            console.error('Error saving cart:', error);
        }
    }

    // Broadcast cart changes to other tabs/windows
    broadcastCartChange(specificBookId = null) {
        // Dispatch a custom event for same-window synchronization
        const event = new CustomEvent('cartChanged', {
            detail: { 
                cart: this.cart, 
                specificBookId: specificBookId 
            }
        });
        window.dispatchEvent(event);
        
        // Also trigger storage event for cross-tab communication
        // We create a fake storage event to force synchronization
        setTimeout(() => {
            window.dispatchEvent(new StorageEvent('storage', {
                key: 'borrowCart',
                newValue: JSON.stringify(this.cart),
                oldValue: null,
                storageArea: localStorage
            }));
        }, 10);
    }

    addBook(bookData) {
        console.log('CartManager.addBook called with:', bookData);
        
        // First check if user is logged in
        if (!this.isUserLoggedIn()) {
            showNotification('Bạn cần đăng nhập để thêm sách vào đơn mượn!', 'warning');
            this.redirectToLogin();
            return { success: false, message: 'Cần đăng nhập để thêm sách' };
        }

        const { id, title, author, image } = bookData;
        
        // Check if book is currently borrowed by user
        if (this.borrowedBooks.includes(id.toString())) {
            return { success: false, message: 'Bạn đang mượn sách này!' };
        }
        
        // Check if book is pending approval
        if (this.pendingBooks.includes(id.toString())) {
            return { success: false, message: 'Sách này đang chờ duyệt!' };
        }
        
        // Check if book already exists
        if (this.cart.some(book => book.id === id)) {
            return { success: false, message: 'Sách đã có trong đơn mượn!' };
        }

        // Check maximum limit
        if (this.cart.length >= 5) {
            return { success: false, message: 'Bạn chỉ có thể mượn tối đa 5 cuốn sách!' };
        }

        // Add book to cart
        this.cart.push({
            id: id,
            title: title || 'Không có tiêu đề',
            author: author || 'Không rõ tác giả',
            image: image || '/static/images/book_default.jpg'
        });

        console.log('Book added to cart. New cart:', this.cart);
        this.saveCart(id); // Chỉ cập nhật nút của sách này
        return { success: true, message: 'Đã thêm sách vào đơn mượn!' };
    }

    removeBook(bookId) {
        this.cart = this.cart.filter(book => book.id !== bookId);
        this.saveCart(bookId); // Cập nhật nút của sách được xóa
    }

    clearCart() {
        this.cart = [];
        this.saveCart();
    }

    isInCart(bookId) {
        return this.cart.some(book => book.id === bookId);
    }

    getCart() {
        return [...this.cart]; // Return a copy
    }

    getCartCount() {
        return this.cart.length;
    }

    // Update all add-to-cart buttons on the page
    updateAllButtons() {
        const buttons = document.querySelectorAll('.add-to-cart');
        buttons.forEach(button => {
            // Gọi updateButtonState không có specificBookId để cập nhật tất cả
            this.updateButtonState(button);
        });

        // Update cart count displays
        this.updateCartCountDisplays();
    }

    // Update button for a specific book only
    updateBookButton(bookId) {
        const buttons = document.querySelectorAll(`[data-book-id="${bookId}"], [data-id="${bookId}"]`);
        buttons.forEach(button => {
            if (button.classList.contains('add-to-cart')) {
                this.updateButtonState(button, bookId);
            }
        });
        
        // Update cart count displays
        this.updateCartCountDisplays();
    }

    /**
     * Update the state of a cart button based on book status
     * Button states (in priority order):
     * 1. .borrowed - Amber styling for books currently borrowed by user
     * 2. .pending - Orange styling for books pending approval
     * 3. :disabled (no class) - Gray styling for out of stock books  
     * 4. .in-cart - Green styling for books already in cart
     * 5. Default state - Blue styling for available books
     * 
     * CSS classes are defined in style.css for consistent styling across pages
     * @param {HTMLElement} button The button element to update
     * @param {string|null} specificBookId Optional specific book ID to update
     */
    updateButtonState(button, specificBookId = null) {
        const buttonBookId = button.getAttribute('data-book-id') || button.getAttribute('data-id');
        
        // Nếu có specificBookId, chỉ cập nhật nút của sách đó
        if (specificBookId && buttonBookId !== specificBookId && buttonBookId !== specificBookId.toString()) {
            return;
        }
        
        // Nếu không có buttonBookId, bỏ qua nút này
        if (!buttonBookId) {
            return;
        }

        const isInCart = this.isInCart(buttonBookId);
        const isBorrowed = this.borrowedBooks.includes(buttonBookId.toString());
        const isPending = this.pendingBooks.includes(buttonBookId.toString());
        
        // Kiểm tra trạng thái availability từ DOM để tránh ghi đè trạng thái "Hết sách"
        const bookCard = button.closest('.book-card');
        const isOutOfStock = bookCard && bookCard.querySelector('.book-status.unavailable');
        
        if (isBorrowed) {
            // Sách đang mượn -> nút disabled với "Đang mượn"
            button.classList.remove('in-cart', 'pending');
            button.classList.add('borrowed');
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-book-reader"></i> Đang mượn';
            // Remove inline styles - let CSS classes handle styling
            // button.style.backgroundColor = '';
            // button.style.color = '';
            
            // Add book card state class for visual feedback
            if (bookCard) {
                bookCard.classList.add('borrowed');
                bookCard.classList.remove('in-cart', 'pending');
            }
        } else if (isPending) {
            // Sách đang chờ duyệt -> nút disabled với "Chờ duyệt"
            button.classList.remove('in-cart', 'borrowed');
            button.classList.add('pending');
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-clock"></i> Chờ duyệt';
            // Remove inline styles - let CSS classes handle styling
            button.style.backgroundColor = '';
            button.style.color = '';
            
            // Add book card state class for visual feedback
            if (bookCard) {
                bookCard.classList.add('pending');
                bookCard.classList.remove('in-cart', 'borrowed');
            }
        } else if (isOutOfStock) {
            // Sách hết -> nút disabled với "Hết sách"
            button.classList.remove('in-cart', 'borrowed', 'pending');
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-times"></i> Hết sách';
            // Remove inline styles - let CSS classes handle styling
            button.style.backgroundColor = '';
            button.style.color = '';
            
            // Remove book card state classes
            if (bookCard) {
                bookCard.classList.remove('in-cart', 'borrowed', 'pending');
            }
        } else if (isInCart) {
            // Sách đã trong giỏ -> nút "Đã thêm"
            button.classList.add('in-cart');
            button.classList.remove('borrowed', 'pending');
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-check"></i> Đã thêm';
            // Remove inline styles - let CSS classes handle styling
            button.style.backgroundColor = '';
            button.style.color = '';
            
            // Add book card state class for visual feedback
            if (bookCard) {
                bookCard.classList.add('in-cart');
                bookCard.classList.remove('borrowed', 'pending');
            }
        } else {
            // Sách chưa trong giỏ và có sẵn -> nút "Thêm vào đơn"
            button.classList.remove('in-cart', 'borrowed', 'pending');
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-plus"></i> Thêm vào đơn';
            // Remove inline styles - let CSS classes handle styling
            button.style.backgroundColor = '';
            button.style.color = '';
            
            // Remove book card state classes
            if (bookCard) {
                bookCard.classList.remove('in-cart', 'borrowed', 'pending');
            }
        }
    }

    updateCartCountDisplays() {
        const count = this.getCartCount();
        const cartCountElements = document.querySelectorAll('#cart-count, .cart-count');
        
        cartCountElements.forEach(element => {
            if (element.tagName === 'SPAN' && element.parentElement && element.parentElement.textContent.includes('Đơn mượn của bạn')) {
                element.textContent = `(${count})`;
            } else {
                element.textContent = count;
            }
            
            // Show/hide based on count
            if (count > 0) {
                element.style.display = 'inline-block';
            } else {
                element.style.display = 'none';
            }
        });
    }

    // Sync cart with server (if needed)
    syncCart() {
        this.loadCart();
        this.loadBorrowedBooks(); // Also reload borrowed books
        this.loadPendingBooks(); // Also reload pending books
        this.updateAllButtons();
        
        // Update cart UI if it exists on the page
        if (typeof updateCartUI === 'function') {
            updateCartUI();
        }
    }

    // Add event listener for cart changes
    addEventListener(callback) {
        this.eventListeners.push(callback);
    }

    // Notify all listeners of cart changes
    notifyListeners() {
        this.eventListeners.forEach(callback => {
            try {
                callback(this.getCart());
            } catch (error) {
                console.error('Error in cart listener:', error);
            }
        });
    }

    // Check if user is logged in
    isUserLoggedIn() {
        return !!localStorage.getItem('access_token') || 
               document.cookie.split(';').some(c => c.trim().startsWith('access_token='));
    }

    // Redirect to login page
    redirectToLogin(returnUrl) {
        const currentPage = returnUrl || window.location.pathname;
        window.location.href = `/login?next=${encodeURIComponent(currentPage)}`;
    }

    loadBorrowedBooks() {
        // Only load if user is logged in
        if (!this.isUserLoggedIn()) {
            this.borrowedBooks = [];
            return;
        }

        // Get access token
        const getCookie = (name) => {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };

        const accessToken = getCookie('access_token');
        if (!accessToken) {
            this.borrowedBooks = [];
            return;
        }

        // Fetch active borrow orders from API instead of individual borrows
        fetch('/api/borrow-orders/my-orders?status=active', {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch borrowed books');
            }
            return response.json();
        })
        .then(orders => {
            // Extract book IDs from active orders
            this.borrowedBooks = [];
            orders.forEach(order => {
                if (order.status === 'active' && order.books) {
                    order.books.forEach(book => {
                        this.borrowedBooks.push(book.id.toString());
                    });
                }
            });
            
            // Update buttons after loading borrowed books
            this.updateAllButtons();
        })
        .catch(error => {
            console.error('Error loading borrowed books:', error);
            this.borrowedBooks = [];
        });
    }

    /**
     * Load pending books (books in pending borrow orders) from server
     */
    loadPendingBooks() {
        // Check if user is logged in
        if (!this.isUserLoggedIn()) {
            this.pendingBooks = [];
            return;
        }

        // Get access token
        const getCookie = (name) => {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        };

        const accessToken = getCookie('access_token');
        if (!accessToken) {
            this.pendingBooks = [];
            return;
        }

        // Fetch pending borrow orders from API
        fetch('/api/borrow-orders/my-orders?status=pending', {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch pending orders');
            }
            return response.json();
        })
        .then(orders => {
            // Extract book IDs from pending orders
            this.pendingBooks = [];
            orders.forEach(order => {
                if (order.status === 'pending' && order.books) {
                    order.books.forEach(book => {
                        this.pendingBooks.push(book.id.toString());
                    });
                }
            });
            
            // Update buttons after loading pending books
            this.updateAllButtons();
        })
        .catch(error => {
            console.error('Error loading pending books:', error);
            this.pendingBooks = [];
        });
    }
}

// Create global cart manager instance
window.cartManager = new CartManager();

// Initialize cart when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Cart.js: DOM Content Loaded - Initializing cart system');
    
    // Initialize the cart (backward compatibility)
    initCart();
    
    // Add event listeners for add-to-cart buttons across the site
    setupCartButtons();
    
    // Update cart UI if it exists on the page
    updateCartUI();
    
    console.log('Cart.js: Cart system initialized successfully');
});

/**
 * Initialize the cart system
 */
function initCart() {
    // If cart doesn't exist in localStorage, create it
    if (!localStorage.getItem('borrowCart')) {
        localStorage.setItem('borrowCart', JSON.stringify([]));
    }
}

/**
 * Get the current cart from localStorage
 */
function getCart() {
    try {
        return JSON.parse(localStorage.getItem('borrowCart')) || [];
    } catch (e) {
        console.error('Error parsing cart from localStorage:', e);
        return [];
    }
}

/**
 * Save the cart to localStorage (backward compatibility)
 */
function saveCart(cart) {
    localStorage.setItem('borrowCart', JSON.stringify(cart));
}

/**
 * Check if user is logged in (backward compatibility)
 */
function isUserLoggedIn() {
    return window.cartManager.isUserLoggedIn();
}

/**
 * Redirect to login page (backward compatibility)
 */
function redirectToLogin(returnUrl) {
    window.cartManager.redirectToLogin(returnUrl);
}

/**
 * Add a book to the cart (using CartManager)
 */
function addBookToCart(bookId, title, author, image) {
    const bookData = {
        id: bookId,
        title: title,
        author: author,
        image: image
    };

    const result = window.cartManager.addBook(bookData);
    
    if (result.success) {
        showNotification(result.message, 'success');
    } else {
        showNotification(result.message, 'warning');
    }
    
    return result.success;
}

/**
 * Add book to cart with validated details (legacy function, deprecated)
 */
function addBookToCartWithDetails(bookId, title, author, image) {
    const bookData = {
        id: bookId,
        title: title,
        author: author,
        image: image || '/static/images/book_default.jpg'
    };
    
    const result = window.cartManager.addBook(bookData);
    
    if (result.success) {
        showNotification(result.message, 'success');
        updateCartUI();
    } else {
        showNotification(result.message, 'warning');
    }
    
    return result.success;
}

/**
 * Fetch book details from server (legacy function, may be used by other parts)
 */
function fetchBookDetails(bookId, callback) {
    fetch(`/api/books/${bookId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Không thể lấy thông tin sách');
            }
            return response.json();
        })
        .then(data => {
            const bookDetails = {
                title: data.title,
                author: data.author.name,
                image: data.cover_image || '/static/images/book_default.jpg'
            };
            callback(bookDetails);
        })
        .catch(error => {
            console.error('Error fetching book details:', error);
            callback(null);
        });
}

/**
 * Remove a book from the cart (using CartManager)
 */
function removeBookFromCart(bookId) {
    window.cartManager.removeBook(bookId);
    showNotification('Đã xóa sách khỏi đơn mượn', 'info');
    updateCartUI();
    return true;
}

/**
 * Clear the entire cart (using CartManager)
 */
function clearCart() {
    window.cartManager.clearCart();
    showNotification('Đã xóa tất cả sách khỏi đơn mượn', 'info');
    updateCartUI();
}

/**
 * Get the current cart from CartManager
 */
function getCart() {
    return window.cartManager.getCart();
}

/**
 * Update the cart UI elements if they exist on the page
 */
function updateCartUI() {
    const cart = getCart();
    
    // Update cart count if element exists
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        cartCount.textContent = `(${cart.length})`;
    }
    
    // Update cart items if element exists
    const cartItems = document.getElementById('cart-items');
    const emptyCart = document.getElementById('empty-cart');
    const submitOrderBtn = document.getElementById('submit-order');
    
    if (cartItems) {
        // Show/hide empty cart message
        if (cart.length === 0) {
            if (emptyCart) emptyCart.style.display = 'flex';
            cartItems.style.display = 'none';
            if (submitOrderBtn) submitOrderBtn.disabled = true;
        } else {
            if (emptyCart) emptyCart.style.display = 'none';
            cartItems.style.display = 'block';
            if (submitOrderBtn) submitOrderBtn.disabled = false;
        }
        
        // Update cart items
        cartItems.innerHTML = '';
        cart.forEach(book => {
            const cartItem = document.createElement('div');
            cartItem.className = 'cart-item';
            cartItem.innerHTML = `
                <div class="cart-item-cover">
                    <img src="${book.image}" alt="${book.title}">
                </div>
                <div class="cart-item-info">
                    <h5>${book.title}</h5>
                    <p>${book.author}</p>
                    <button class="btn btn-sm btn-danger remove-from-cart" data-id="${book.id}">
                        <i class="fas fa-trash"></i> Xóa
                    </button>
                </div>
            `;
            cartItems.appendChild(cartItem);
            
            // Add event listener for remove button
            const removeBtn = cartItem.querySelector('.remove-from-cart');
            removeBtn.addEventListener('click', function() {
                removeBookFromCart(book.id);
            });
        });
    }
    
    // Update add-to-cart buttons state
    updateAddButtons();
}

/**
 * Update the state of all add-to-cart buttons on the page (using CartManager)
 */
function updateAddButtons() {
    window.cartManager.updateAllButtons();
}

/**
 * Setup event listeners for add-to-cart buttons
 */
function setupCartButtons() {
    console.log('Cart.js: Setting up cart button event listeners');
    
    // Setup all add-to-cart buttons using CartManager approach
    setTimeout(() => {
        const buttons = document.querySelectorAll('.add-to-cart');
        buttons.forEach(button => {
            // Remove existing listeners to prevent duplicates
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            // Add new listener
            newButton.addEventListener('click', function(e) {
                e.preventDefault();
                const bookId = this.getAttribute('data-book-id') || this.getAttribute('data-id');
                if (bookId) {
                    // Get book data from DOM
                    const bookCard = document.querySelector(`[data-id="${bookId}"], [data-book-id="${bookId}"]`);
                    if (bookCard) {
                        const bookData = {
                            id: bookId,
                            title: bookCard.getAttribute('data-title'),
                            author: bookCard.getAttribute('data-author'),
                            image: bookCard.getAttribute('data-image')
                        };
                        
                        const result = window.cartManager.addBook(bookData);
                        
                        if (result.success) {
                            showNotification(result.message, 'success');
                        } else {
                            showNotification(result.message, 'warning');
                        }
                    }
                }
            });
        });
        
        // Initial sync
        window.cartManager.updateAllButtons();
    }, 100);
    
    // Handle borrow-now-btn in detail page  
    const borrowNowBtn = document.getElementById('borrow-now-btn');
    if (borrowNowBtn) {
        borrowNowBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get book info from the page
            const bookId = window.location.pathname.split('/').pop();
            const title = document.querySelector('.book-title').textContent;
            const author = document.querySelector('.book-author').textContent.replace('Tác giả: ', '');
            const image = document.querySelector('.book-cover img').getAttribute('src');
            
            const bookData = {
                id: bookId,
                title: title,
                author: author,
                image: image
            };
            
            const result = window.cartManager.addBook(bookData);
            
            if (result.success) {
                showNotification(result.message, 'success');
                // Redirect to borrow page
                window.location.href = '/borrow';
            } else {
                showNotification(result.message, 'warning');
            }
        });
    }
}

// Global functions for backward compatibility
window.addToCart = function(bookId) {
    const bookCard = document.querySelector(`[data-id="${bookId}"], [data-book-id="${bookId}"]`);
    if (!bookCard) {
        console.error('Book card not found for ID:', bookId);
        return;
    }

    const bookData = {
        id: bookId,
        title: bookCard.getAttribute('data-title'),
        author: bookCard.getAttribute('data-author'),
        image: bookCard.getAttribute('data-image')
    };

    const result = window.cartManager.addBook(bookData);
    
    if (result.success) {
        showNotification(result.message, 'success');
    } else {
        showNotification(result.message, 'warning');
    }
};


window.updateCartCount = function() {
    window.cartManager.updateCartCountDisplays();
};

/**
 * Show a notification to the user
 */
function showNotification(message, type) {
    // Use SweetAlert if available
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
        // Fallback to alert
        alert(message);
    }
}