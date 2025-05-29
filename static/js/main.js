/**
 * JavaScript chung cho toàn bộ trang web
 */
document.addEventListener('DOMContentLoaded', function() {
    // Kiểm tra đăng nhập
    const authToken = localStorage.getItem('access_token');
    const isLoggedIn = !!authToken;
    
    // Cập nhật UI tùy theo trạng thái đăng nhập
    updateAuthUI(isLoggedIn);
    
    // Khởi tạo tìm kiếm trên thanh header
    initSearchBar();
    
    // Xử lý đăng xuấp
    setupLogout();
});

/**
 * Cập nhật UI dựa trên trạng thái đăng nhập
 */
function updateAuthUI(isLoggedIn) {
    const authLinks = document.querySelector('.nav-links');
    
    if (!authLinks) return;
    
    // Lấy các phần tử cần cập nhật
    let loginLink = authLinks.querySelector('a[href="/login"]');
    if (!loginLink) {
        loginLink = document.createElement('li');
        loginLink.innerHTML = '<a href="/login"><i class="fas fa-user"></i> Đăng Nhập</a>';
    } else {
        loginLink = loginLink.parentElement;
    }
    
    // Nếu đã đăng nhập, hiển thị menu user
    if (isLoggedIn) {
        const userMenu = `
            <li class="user-menu">
                <a href="/profile"><i class="fas fa-user-circle"></i> Tài khoản</a>
                <ul class="dropdown-menu">
                    <li><a href="/profile">Thông tin cá nhân</a></li>
                    <li><a href="/profile#borrows">Sách đang mượn</a></li>
                    <li><a href="/profile#history">Lịch sử mượn</a></li>
                    <li><a href="#" id="logout-btn">Đăng xuất</a></li>
                </ul>
            </li>
        `;
        
        // Thay thế link đăng nhập bằng menu user
        if (loginLink) {
            loginLink.outerHTML = userMenu;
        } else {
            authLinks.insertAdjacentHTML('beforeend', userMenu);
        }
    }
}

/**
 * Khởi tạo thanh tìm kiếm
 */
function initSearchBar() {
    const searchForm = document.querySelector('.search-bar');
    if (!searchForm) return;
    
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const input = searchForm.querySelector('input');
        if (!input || !input.value.trim()) return;
        
        window.location.href = `/search?q=${encodeURIComponent(input.value.trim())}`;
    });
}

/**
 * Xử lý đăng xuất
 */
function setupLogout() {
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'logout-btn') {
            e.preventDefault();
            
            // Xóa token từ localStorage
            localStorage.removeItem('access_token');
            
            // Xóa token từ cookies
            document.cookie = 'access_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
            
            // Refresh trang
            window.location.href = '/';
        }
    });
}

/**
 * Gửi request API với token xác thực
 */
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('access_token');
    
    // Get base URL from current location
    const baseUrl = window.location.protocol + '//' + window.location.host;
    
    // Ensure URL is absolute
    const fullUrl = url.startsWith('http') ? url : `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`;
    
    // Thiết lập headers
    const headers = options.headers || {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Thêm Content-Type mặc định nếu là POST/PUT và body là object
    if (
        ['POST', 'PUT'].includes(options.method) && 
        options.body && 
        typeof options.body === 'object' &&
        !(options.body instanceof FormData)
    ) {
        headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
    }
    
    // Gửi request
    const response = await fetch(fullUrl, {
        ...options,
        headers
    });
    
    // Kiểm tra lỗi
    if (!response.ok) {
        if (response.status === 401) {
            // Hết hạn token, đăng xuất
            localStorage.removeItem('access_token');
            window.location.href = '/login';
            throw new Error('Phiên đăng nhập hết hạn');
        }
        
        const error = await response.json();
        throw new Error(error.detail || 'Có lỗi xảy ra');
    }
    
    // Trả về dữ liệu
    return await response.json();
}