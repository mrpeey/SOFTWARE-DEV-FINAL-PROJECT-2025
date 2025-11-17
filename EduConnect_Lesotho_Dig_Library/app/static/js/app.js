/**
 * EduConnect Lesotho Digital Library - Main JavaScript
 * Enhanced functionality for library management system
 */

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeLibraryFeatures();
    
    // Set overlay color from data attribute for all category overlays
    document.querySelectorAll('.category-overlay').forEach(function(overlay) {
    
    // Fetch and render reviews dynamically if on book detail page
    if (document.getElementById('dynamic-reviews')) {
        const bookId = window.bookId || getBookIdFromURL();
        if (bookId) {
            fetchReviews(bookId);
        }
    }
        var color = overlay.getAttribute('data-overlay-color');
        if (color) {
            overlay.style.background = color;
        }
    });
});

/**
 * Initialize all library-specific features
 */
function initializeLibraryFeatures() {
    // Initialize search functionality
    initializeSearch();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize tooltips and popovers
    initializeBootstrapComponents();
    
    // Initialize book interaction features
    initializeBookFeatures();
    
    // Initialize notification system
    initializeNotifications();
    
    // Initialize offline features
    initializeOfflineFeatures();
    
    // Initialize accessibility features
    initializeAccessibility();
}

/**
 * Enhanced search functionality with debouncing
 */
function initializeSearch() {
    const searchInput = document.getElementById('search-input');
    const searchForm = document.getElementById('search-form');
    
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();
            
            if (query.length >= 2) {
                searchTimeout = setTimeout(() => {
                    performLiveSearch(query);
                }, 300);
            } else {
                clearSearchResults();
            }
        });
        
        // Handle Enter key
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (searchForm) {
                    searchForm.submit();
                }
            }
        });
    }
}

/**
 * Perform live search with AJAX
 */
function performLiveSearch(query) {
    const resultsContainer = document.getElementById('live-search-results');
    if (!resultsContainer) return;
    
    // Show loading state
    resultsContainer.innerHTML = '<div class="text-center p-3"><div class="loading"></div> Searching...</div>';
    resultsContainer.style.display = 'block';
    
    fetch(`/api/search?q=${encodeURIComponent(query)}&live=true`)
        .then(response => response.json())
        .then(data => {
            displayLiveSearchResults(data.books || []);
        })
        .catch(error => {
            console.error('Search error:', error);
            resultsContainer.innerHTML = '<div class="text-muted p-3">Search unavailable</div>';
        });
}

/**
 * Display live search results
 */
function displayLiveSearchResults(books) {
    const resultsContainer = document.getElementById('live-search-results');
    if (!resultsContainer) return;
    
    if (books.length === 0) {
        resultsContainer.innerHTML = '<div class="text-muted p-3">No books found</div>';
        return;
    }
    
    const html = books.map(book => `
        <div class="search-result-item p-2 border-bottom">
            <div class="d-flex">
                <div class="flex-shrink-0 me-3">
                    <img src="${book.cover_url || '/static/images/book-placeholder.png'}" 
                         alt="${book.title}" class="search-result-cover">
                </div>
                <div class="flex-grow-1">
                    <h6 class="mb-1">
                        <a href="/books/${book.id}" class="text-decoration-none">${book.title}</a>
                    </h6>
                    <p class="mb-1 text-muted small">${book.author || 'Unknown Author'}</p>
                    <small class="text-muted">${book.category || 'Uncategorized'}</small>
                </div>
            </div>
        </div>
    `).join('');
    
    resultsContainer.innerHTML = html;
}

/**
 * Clear search results
 */
function clearSearchResults() {
    const resultsContainer = document.getElementById('live-search-results');
    if (resultsContainer) {
        resultsContainer.style.display = 'none';
        resultsContainer.innerHTML = '';
    }
}

/**
 * Initialize form validation with better UX
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            
            form.classList.add('was-validated');
        });
        
        // Real-time validation
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    });
}

/**
 * Initialize Bootstrap components
 */
function initializeBootstrapComponents() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.forEach(function (popoverTriggerEl) {
        new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Book-specific features
 */
function initializeBookFeatures() {
    // Book borrowing
    initializeBorrowingFeatures();
    
    // Book reviews
    initializeReviewFeatures();
    
    // Book downloads
    initializeDownloadFeatures();
    
    // Book favorites
    initializeFavoriteFeatures();
}

/**
 * Initialize borrowing features
 */
function initializeBorrowingFeatures() {
    const borrowButtons = document.querySelectorAll('.btn-borrow');
    
    borrowButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const bookId = this.dataset.bookId;
            borrowBook(bookId, this);
        });
    });
}

/**
 * Borrow book function
 */
function borrowBook(bookId, button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<div class="loading"></div> Borrowing...';
    button.disabled = true;
    
    fetch('/api/borrow', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ book_id: bookId })
    })
    .then(async response => {
        if (!response.ok) {
            let msg = `Error: ${response.status}`;
            if (response.status === 401) msg = 'You must be logged in to borrow books.';
            else if (response.status === 403) msg = 'You are not allowed to borrow this book.';
            else if (response.status === 409) msg = 'You have already borrowed this book.';
            showNotification(msg, 'error');
            button.innerHTML = originalText;
            button.disabled = false;
            return;
        }
        const data = await response.json();
        if (data.success) {
            showNotification('Book borrowed successfully!', 'success');
            button.innerHTML = 'Borrowed';
            button.classList.remove('btn-primary');
            button.classList.add('btn-success');
        } else {
            showNotification(data.message || 'Failed to borrow book', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        showNotification('Network error: Unable to borrow book. Please try again.', 'error');
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

/**
 * Initialize review features
 */
function initializeReviewFeatures() {
    // Star rating system
    const starRatings = document.querySelectorAll('.star-rating');
    
    starRatings.forEach(rating => {
        const stars = rating.querySelectorAll('.star');
        const input = rating.querySelector('input[type="hidden"]');
        
        stars.forEach((star, index) => {
            star.addEventListener('click', function() {
                const ratingValue = index + 1;
                input.value = ratingValue;
                updateStarDisplay(stars, ratingValue);
            });
            
            star.addEventListener('mouseover', function() {
                updateStarDisplay(stars, index + 1, true);
            });
        });
        
        rating.addEventListener('mouseleave', function() {
            updateStarDisplay(stars, input.value);
        });
    });
}

/**
 * Update star display
 */
function updateStarDisplay(stars, rating, isHover = false) {
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add(isHover ? 'star-hover' : 'star-active');
            star.classList.remove(isHover ? 'star-active' : 'star-hover');
        } else {
            star.classList.remove('star-active', 'star-hover');
        }
    });
}

/**
 * Initialize download features
 */
function initializeDownloadFeatures() {
    const downloadButtons = document.querySelectorAll('.btn-download');
    
    downloadButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const bookId = this.dataset.bookId;
            downloadBook(bookId, this);
        });
    });
}

/**
 * Download book function
 */
function downloadBook(bookId, button) {
    const originalText = button.innerHTML;
    button.innerHTML = '<div class="loading"></div> Preparing...';
    button.disabled = true;
    
    // Create a temporary link for download
    const link = document.createElement('a');
    link.href = `/api/download/${bookId}`;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Reset button after a short delay
    setTimeout(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    }, 2000);
}

/**
 * Initialize favorite features
 */
function initializeFavoriteFeatures() {
    const favoriteButtons = document.querySelectorAll('.btn-favorite');
    
    favoriteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const bookId = this.dataset.bookId;
            toggleFavorite(bookId, this);
        });
    });
}

/**
 * Toggle favorite status
 */
function toggleFavorite(bookId, button) {
    const isFavorite = button.classList.contains('favorited');
    
    fetch(`/api/books/${bookId}/favorite`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ 
            book_id: bookId,
            action: isFavorite ? 'remove' : 'add'
        })
    })
    .then(async response => {
        if (!response.ok) {
            let msg = `Error: ${response.status}`;
            if (response.status === 401) msg = 'You must be logged in to update favorites.';
            else if (response.status === 403) msg = 'You are not allowed to update favorites.';
            else if (response.status === 404) msg = 'Book not found.';
            showNotification(msg, 'error');
            return;
        }
        const data = await response.json();
        if (data.success) {
            button.classList.toggle('favorited');
            const icon = button.querySelector('i');
            if (button.classList.contains('favorited')) {
                icon.classList.remove('far');
                icon.classList.add('fas');
                showNotification('Added to favorites', 'success');
            } else {
                icon.classList.remove('fas');
                icon.classList.add('far');
                showNotification('Removed from favorites', 'info');
            }
        } else {
            showNotification(data.message || 'Failed to update favorites', 'error');
        }
    })
    .catch(error => {
        showNotification('Network error: Unable to update favorites. Please try again.', 'error');
    });
}

/**
 * Initialize notification system
 */
function initializeNotifications() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert[data-auto-hide]');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });
    
    // Check for new notifications periodically (if user is logged in)
    if (document.body.dataset.userLoggedIn === 'true') {
        setInterval(checkNotifications, 30000); // Check every 30 seconds
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const alertClass = `alert-${type === 'error' ? 'danger' : type}`;
    const notification = document.createElement('div');
    notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

/**
 * Check for new notifications
 */
function checkNotifications() {
    fetch('/api/notifications/check')
        .then(response => response.json())
        .then(data => {
            if (data.new_count > 0) {
                updateNotificationBadge(data.new_count);
            }
        })
        .catch(error => {
            console.error('Notification check error:', error);
        });
}

/**
 * Update notification badge
 */
function updateNotificationBadge(count) {
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

/**
 * Initialize offline features
 */
function initializeOfflineFeatures() {
    // Check online status
    window.addEventListener('online', handleOnlineStatus);
    window.addEventListener('offline', handleOfflineStatus);
    
    // Initialize service worker if supported
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/sw.js')
            .then(registration => {
                console.log('Service Worker registered successfully');
            })
            .catch(error => {
                console.log('Service Worker registration failed:', error);
            });
    }
}

/**
 * Handle online status
 */
function handleOnlineStatus() {
    showNotification('You are back online!', 'success');
    // Sync any pending offline actions
    syncOfflineActions();
}

/**
 * Handle offline status
 */
function handleOfflineStatus() {
    showNotification('You are now offline. Some features may be limited.', 'warning');
}

/**
 * Sync offline actions when back online
 */
function syncOfflineActions() {
    // Check if there are any pending actions in localStorage
    const pendingActions = JSON.parse(localStorage.getItem('pendingActions') || '[]');
    
    if (pendingActions.length > 0) {
        // Process each pending action
        pendingActions.forEach(action => {
            // Implementation depends on action type
            console.log('Syncing action:', action);
        });
        
        // Clear pending actions
        localStorage.removeItem('pendingActions');
    }
}

/**
 * Initialize accessibility features
 */
function initializeAccessibility() {
    // Keyboard navigation improvements
    document.addEventListener('keydown', function(e) {
        // Skip links for screen readers
        if (e.key === 'Tab' && e.shiftKey && document.activeElement === document.body) {
            const skipLink = document.querySelector('.skip-link');
            if (skipLink) {
                skipLink.focus();
            }
        }
    });
    
    // High contrast mode detection
    if (window.matchMedia && window.matchMedia('(prefers-contrast: high)').matches) {
        document.body.classList.add('high-contrast');
    }
    
    // Reduced motion detection
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        document.body.classList.add('reduced-motion');
    }
    
    // Accessibility: trap focus in modals
    function trapModalFocus(modalId) {
        var modal = document.getElementById(modalId);
        if (!modal) return;
        modal.addEventListener('shown.bs.modal', function () {
            var input = modal.querySelector('input, textarea, button, select');
            if (input) input.focus();
        });
    }
    document.addEventListener('DOMContentLoaded', function() {
        trapModalFocus('aiChatModal');
    });
}

/**
 * Utility function to get CSRF token
 */
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

/**
 * Utility function for debouncing
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Utility function for API calls
 */
function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    };
    
    return fetch(url, { ...defaultOptions, ...options })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        });
}

// Fade-in effect for cards on load
function fadeInCards() {
    document.querySelectorAll('.card').forEach(function(card, i) {
        card.style.opacity = 0;
        setTimeout(function() {
            card.style.transition = 'opacity 0.7s';
            card.style.opacity = 1;
        }, 100 + i * 80);
    });
}
document.addEventListener('DOMContentLoaded', fadeInCards);

// Export functions for global access if needed
window.LibraryJS = {
    showNotification,
    borrowBook,
    downloadBook,
    toggleFavorite,
    apiCall
};

// Share button functionality for book detail page
document.addEventListener('DOMContentLoaded', function() {
    var shareBtn = document.getElementById('shareBtn');
    var shareModal = document.getElementById('shareModal');
    if (shareBtn && shareModal) {
        shareBtn.addEventListener('click', function() {
            var modal = new bootstrap.Modal(shareModal);
            modal.show();
            // Prepare share links
            var bookUrl = window.location.href;
            var bookTitle = document.querySelector('h2') ? document.querySelector('h2').innerText : 'Book';
            document.getElementById('shareEmail').href = `mailto:?subject=Check out this book: ${encodeURIComponent(bookTitle)}&body=Read it here: ${encodeURIComponent(bookUrl)}`;
            document.getElementById('shareWhatsApp').href = `https://wa.me/?text=${encodeURIComponent('Check out this book: ' + bookTitle + ' ' + bookUrl)}`;
            document.getElementById('shareFacebook').href = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(bookUrl)}`;
            document.getElementById('shareCopy').onclick = function() {
                navigator.clipboard.writeText(bookUrl);
                this.innerText = 'Link Copied!';
                setTimeout(() => { this.innerText = 'Copy Link'; }, 1500);
            };
        });
    }
});