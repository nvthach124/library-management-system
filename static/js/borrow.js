document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const booksGrid = document.getElementById('books-grid');
    const searchInput = document.getElementById('search-input');
    const categoryFilter = document.getElementById('category-filter');
    const cartContainer = document.getElementById('cart-container');
    const cartItems = document.getElementById('cart-items');
    const cartCounter = document.getElementById('cart-counter');
    const totalItems = document.getElementById('total-items');
    const checkoutBtn = document.getElementById('checkout-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const notesInput = document.getElementById('notes');
    const emptyCartMsg = document.getElementById('empty-cart-msg');
    
    // State
    let cart = [];
    const MAX_BOOKS = 5;
    
    // Initialize
    updateCart();
    
    // Event listeners
    if (searchInput) {
        searchInput.addEventListener('input', filterBooks);
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterBooks);
    }
    
    if (booksGrid) {
        booksGrid.addEventListener('click', function(e) {
            const addBtn = e.target.closest('.add-to-cart');
            if (addBtn) {
                e.preventDefault();
                addToCart(addBtn);
            }
        });
    }
    
    if (cartItems) {
        cartItems.addEventListener('click', function(e) {
            const removeBtn = e.target.closest('.remove-item');
            if (removeBtn) {
                e.preventDefault();
                const bookId = parseInt(removeBtn.getAttribute('data-id'));
                removeFromCart(bookId);
            }
        });
    }
    
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', checkout);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', clearCart);
    }
    
    // Functions
    function addToCart(btn) {
        const bookCard = btn.closest('.book-card');
        if (!bookCard) return;
        
        const bookId = parseInt(btn.getAttribute('data-book-id') || bookCard.getAttribute('data-id'));
        const title = bookCard.getAttribute('data-title');
        const author = bookCard.getAttribute('data-author');
        const cover = bookCard.querySelector('.book-cover').getAttribute('src');
        
        // Check if book is already in cart
        if (cart.find(item => item.id === bookId)) {
            showToast('Sách này đã có trong giỏ mượn', 'warning');
            return;
        }
        
        // Check if cart is full (maximum 5 books)
        if (cart.length >= MAX_BOOKS) {
            showToast(`Giỏ mượn đã đầy. Bạn chỉ được mượn tối đa ${MAX_BOOKS} cuốn sách mỗi lần.`, 'warning');
            return;
        }
        
        // Add to cart
        cart.push({
            id: bookId,
            title: title,
            author: author,
            cover: cover
        });
        
        updateCart();
        showToast('Đã thêm sách vào giỏ mượn', 'success');
        
        // Disable add button for this book
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-check"></i> Đã thêm';
    }
    
    function removeFromCart(bookId) {
        cart = cart.filter(item => item.id !== bookId);
        updateCart();
        
        // Re-enable add button for this book
        const bookCard = document.querySelector(`.book-card[data-id="${bookId}"]`) || 
                          document.querySelector(`.book-card[data-book-id="${bookId}"]`);
        if (bookCard) {
            const addBtn = bookCard.querySelector('.add-to-cart');
            if (addBtn) {
                addBtn.disabled = false;
                addBtn.innerHTML = '<i class="fas fa-plus"></i> Thêm vào đơn';
            }
        }
    }
    
    function updateCart() {
        // Update counter
        const count = cart.length;
        cartCounter.textContent = count;
        totalItems.textContent = count;
        
        // Show/hide empty cart message
        if (count === 0) {
            emptyCartMsg.style.display = 'block';
            cartItems.style.display = 'none';
            checkoutBtn.disabled = true;
        } else {
            emptyCartMsg.style.display = 'none';
            cartItems.style.display = 'block';
            checkoutBtn.disabled = false;
        }
        
        // Update cart items
        cartItems.innerHTML = '';
        cart.forEach(item => {
            const itemElement = document.createElement('div');
            itemElement.className = 'cart-item';
            itemElement.innerHTML = `
                <div class="item-image">
                    <img src="${item.cover}" alt="${item.title}">
                </div>
                <div class="item-info">
                    <h4 class="item-title">${item.title}</h4>
                    <p class="item-author">${item.author}</p>
                </div>
                <button class="remove-item" data-id="${item.id}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            cartItems.appendChild(itemElement);
        });
        
        // Save cart to localStorage
        localStorage.setItem('borrowCart', JSON.stringify(cart));
    }
    
    function clearCart() {
        // Re-enable all add buttons
        cart.forEach(item => {
            const bookCard = document.querySelector(`.book-card[data-id="${item.id}"]`) || 
                             document.querySelector(`.book-card[data-book-id="${item.id}"]`);
            if (bookCard) {
                const addBtn = bookCard.querySelector('.add-to-cart');
                if (addBtn) {
                    addBtn.disabled = false;
                    addBtn.innerHTML = '<i class="fas fa-plus"></i> Thêm vào đơn';
                }
            }
        });
        
        cart = [];
        updateCart();
        notesInput.value = '';
    }
    
    function checkout() {
        if (cart.length === 0) {
            showToast('Giỏ mượn trống. Vui lòng thêm sách vào giỏ.', 'warning');
            return;
        }
        
        // Get book IDs
        const bookIds = cart.map(item => item.id);
        
        // Prepare data
        const data = {
            book_ids: bookIds,
            notes: notesInput.value.trim()
        };
        
        // Get the current hostname and port
        const baseUrl = window.location.protocol + '//' + window.location.host;
        
        // Show loading
        checkoutBtn.disabled = true;
        checkoutBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang xử lý...';
        
        // Submit order
        fetch(`${baseUrl}/api/borrow-orders`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.detail || 'Có lỗi xảy ra');
                });
            }
            return response.json();
        })
        .then(result => {
            showToast(result.message, 'success');
            
            // Clear cart
            clearCart();
            
            // Reset button
            checkoutBtn.disabled = false;
            checkoutBtn.innerHTML = '<i class="fas fa-check"></i> Hoàn tất đơn mượn';
            
            // Show success message
            Swal.fire({
                title: 'Đã tạo đơn mượn thành công!',
                text: `Vui lòng đợi thủ thư duyệt đơn. Hạn trả sách: ${new Date(result.due_date).toLocaleDateString('vi-VN')}`,
                icon: 'success',
                confirmButtonText: 'OK'
            }).then(() => {
                // Redirect to my-borrows page
                window.location.href = '/my-borrows';
            });
        })
        .catch(error => {
            console.error('Error:', error);
            showToast(error.message, 'error');
            
            // Reset button
            checkoutBtn.disabled = false;
            checkoutBtn.innerHTML = '<i class="fas fa-check"></i> Hoàn tất đơn mượn';
        });
    }
    
    // Load cart from localStorage
    function loadCart() {
        const savedCart = localStorage.getItem('borrowCart');
        if (savedCart) {
            try {
                cart = JSON.parse(savedCart);
                updateCart();
                
                // Disable add buttons for books in cart
                cart.forEach(item => {
                    // Check for both data-id and data-book-id to ensure backward compatibility
                    const bookCard = document.querySelector(`.book-card[data-id="${item.id}"]`) || 
                                    document.querySelector(`.book-card[data-book-id="${item.id}"]`);
                    if (bookCard) {
                        const addBtn = bookCard.querySelector('.add-to-cart');
                        if (addBtn) {
                            addBtn.disabled = true;
                            addBtn.innerHTML = '<i class="fas fa-check"></i> Đã thêm';
                        }
                    }
                });
            } catch (e) {
                console.error('Error loading cart:', e);
                localStorage.removeItem('borrowCart');
            }
        }
    }
    
    function filterBooks() {
        const searchQuery = searchInput.value.toLowerCase();
        const categoryId = categoryFilter.value;
        
        const bookCards = booksGrid.querySelectorAll('.book-card');
        
        bookCards.forEach(card => {
            const title = card.dataset.title.toLowerCase();
            const author = card.dataset.author.toLowerCase();
            const matchesSearch = title.includes(searchQuery) || author.includes(searchQuery);
            
            // Get book categories (needs to be added to data attributes in template)
            const categories = card.dataset.categories ? card.dataset.categories.split(',') : [];
            const matchesCategory = !categoryId || categories.includes(categoryId);
            
            // For now, ignore category filter since we don't have categories in data attributes
            const matchesCategory2 = !categoryId || true;
            
            if (matchesSearch && matchesCategory2) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
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
    
    // Load cart on page load
    loadCart();
});
 