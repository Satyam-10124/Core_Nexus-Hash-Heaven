// Modern JavaScript for OnChain Real Estate AI

document.addEventListener('DOMContentLoaded', function() {
    // Initialize animations
    initAnimations();
    
    // Initialize tooltips and popovers
    initTooltips();
    
    // Format blockchain addresses
    formatBlockchainAddresses();
    
    // Format timestamps
    formatTimestamps();
    
    // Initialize task list filters and search
    initTaskFilters();
    
    // Initialize charts with animations
    initCharts();
    
    // Add scroll animations
    initScrollAnimations();
    
    // Add loading state handlers
    initLoadingStates();
    
    // Add task ID validation
    initTaskValidation();
});

/**
 * Initialize fade and slide animations for page elements
 */
function initAnimations() {
    // Add fade-in class to main content
    const mainContent = document.querySelector('.container');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }
    
    // Add staggered animations to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        // Add a small delay for each card to create a staggered effect
        setTimeout(() => {
            card.classList.add('slide-in-up');
        }, 100 * index);
    });
    
    // Add pulse animation to key action buttons
    const actionButtons = document.querySelectorAll('.btn-primary');
    actionButtons.forEach(button => {
        button.addEventListener('mouseover', function() {
            this.classList.add('pulse');
        });
        button.addEventListener('mouseout', function() {
            this.classList.remove('pulse');
        });
    });
}

/**
 * Initialize Bootstrap tooltips and popovers
 */
function initTooltips() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            animation: true,
            delay: { show: 100, hide: 100 }
        });
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl, {
            trigger: 'focus',
            animation: true
        });
    });
}

/**
 * Format blockchain addresses with truncation and copy functionality
 */
function formatBlockchainAddresses() {
    const addressElements = document.querySelectorAll('.blockchain-address');
    addressElements.forEach(element => {
        const address = element.textContent.trim();
        if (address.length > 10) {
            // Format the display
            element.textContent = `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
            element.setAttribute('title', 'Click to copy full address');
            element.setAttribute('data-bs-toggle', 'tooltip');
            element.setAttribute('data-full-address', address);
            
            // Add copy functionality
            element.style.cursor = 'pointer';
            element.addEventListener('click', function() {
                const fullAddress = this.getAttribute('data-full-address');
                navigator.clipboard.writeText(fullAddress).then(() => {
                    // Update tooltip to show copied state
                    const tooltip = bootstrap.Tooltip.getInstance(this);
                    if (tooltip) {
                        tooltip.dispose();
                    }
                    
                    this.setAttribute('title', 'Address copied!');
                    new bootstrap.Tooltip(this, {
                        trigger: 'manual'
                    }).show();
                    
                    // Reset tooltip after 1.5 seconds
                    setTimeout(() => {
                        const newTooltip = bootstrap.Tooltip.getInstance(this);
                        if (newTooltip) {
                            newTooltip.dispose();
                        }
                        this.setAttribute('title', 'Click to copy full address');
                        new bootstrap.Tooltip(this);
                    }, 1500);
                });
            });
        }
    });
}

/**
 * Format timestamps with relative time
 */
function formatTimestamps() {
    const timestampElements = document.querySelectorAll('.timestamp');
    timestampElements.forEach(element => {
        const timestamp = parseInt(element.getAttribute('data-timestamp'));
        if (!isNaN(timestamp)) {
            const date = new Date(timestamp * 1000);
            
            // Add both absolute and relative time
            const absoluteTime = date.toLocaleString();
            const relativeTime = getRelativeTimeString(date);
            
            element.textContent = relativeTime;
            element.setAttribute('title', absoluteTime);
            element.setAttribute('data-bs-toggle', 'tooltip');
        }
    });
}

/**
 * Convert date to relative time string (e.g., "2 hours ago")
 */
function getRelativeTimeString(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.round(diffMs / 1000);
    const diffMin = Math.round(diffSec / 60);
    const diffHour = Math.round(diffMin / 60);
    const diffDay = Math.round(diffHour / 24);
    
    if (diffSec < 60) {
        return 'just now';
    } else if (diffMin < 60) {
        return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
    } else if (diffHour < 24) {
        return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
    } else if (diffDay < 30) {
        return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
    } else {
        return date.toLocaleDateString();
    }
}

/**
 * Initialize task list filters and search functionality
 */
function initTaskFilters() {
    const taskFilterInput = document.getElementById('taskSearch');
    const taskStatusFilter = document.getElementById('statusFilter');
    
    if (taskFilterInput) {
        taskFilterInput.addEventListener('input', filterTasks);
    }
    
    if (taskStatusFilter) {
        taskStatusFilter.addEventListener('change', filterTasks);
    }
    
    function filterTasks() {
        const searchTerm = taskFilterInput ? taskFilterInput.value.toLowerCase() : '';
        const statusFilter = taskStatusFilter ? taskStatusFilter.value : 'all';
        const taskRows = document.querySelectorAll('table tbody tr');
        
        taskRows.forEach(row => {
            const taskText = row.textContent.toLowerCase();
            const taskStatus = row.querySelector('.badge') ? 
                              row.querySelector('.badge').textContent.toLowerCase() : '';
            
            const matchesSearch = taskText.includes(searchTerm);
            const matchesStatus = statusFilter === 'all' || 
                                 (statusFilter === 'completed' && taskStatus === 'completed') ||
                                 (statusFilter === 'pending' && taskStatus === 'pending');
            
            row.style.display = matchesSearch && matchesStatus ? '' : 'none';
        });
    }
}

/**
 * Initialize charts with animated effects
 */
function initCharts() {
    // Get all chart canvases
    const chartCanvases = document.querySelectorAll('.chart-canvas');
    
    chartCanvases.forEach(canvas => {
        // Get chart type from data attribute
        const chartType = canvas.getAttribute('data-chart-type') || 'bar';
        const chartData = getChartData(canvas, chartType);
        
        if (chartData) {
            createAnimatedChart(canvas, chartType, chartData);
        }
    });
}

/**
 * Get chart data based on canvas data attributes
 */
function getChartData(canvas, chartType) {
    // This is a placeholder function that would normally parse data attributes or fetch data
    // In a real implementation, you'd pull data from your application
    // For now, we'll return some sample data based on chart type
    
    if (chartType === 'bar' || chartType === 'line') {
        return {
            labels: ['Market Analysis', 'Property Valuation', 'Investment Analysis', 'Neighborhood Insights', 'Rental Analysis'],
            datasets: [{
                label: 'Completed Tasks',
                data: [12, 19, 8, 15, 10],
                backgroundColor: 'rgba(99, 102, 241, 0.7)',
                borderColor: 'rgba(99, 102, 241, 1)',
                borderWidth: 2
            }]
        };
    } else if (chartType === 'pie' || chartType === 'doughnut') {
        return {
            labels: ['Completed', 'Pending', 'Failed'],
            datasets: [{
                data: [70, 20, 10],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.7)', // Success
                    'rgba(245, 158, 11, 0.7)', // Warning
                    'rgba(239, 68, 68, 0.7)'   // Danger
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(239, 68, 68, 1)'
                ],
                borderWidth: 2
            }]
        };
    }
    
    return null;
}

/**
 * Create an animated chart
 */
function createAnimatedChart(canvas, chartType, chartData) {
    const ctx = canvas.getContext('2d');
    
    // Common animation options
    const animationOptions = {
        animation: {
            duration: 2000,
            easing: 'easeOutQuart'
        },
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    font: {
                        family: "'Inter', sans-serif",
                        size: 12
                    }
                }
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.9)',
                titleFont: {
                    family: "'Inter', sans-serif",
                    size: 14,
                    weight: 'bold'
                },
                bodyFont: {
                    family: "'Inter', sans-serif",
                    size: 13
                },
                padding: 12,
                cornerRadius: 8
            }
        }
    };
    
    // Specific options based on chart type
    let specificOptions = {};
    
    if (chartType === 'bar') {
        specificOptions = {
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(209, 213, 219, 0.2)'
                    },
                    ticks: {
                        font: {
                            family: "'Inter', sans-serif"
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: "'Inter', sans-serif"
                        }
                    }
                }
            }
        };
    } else if (chartType === 'line') {
        specificOptions = {
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(209, 213, 219, 0.2)'
                    },
                    ticks: {
                        font: {
                            family: "'Inter', sans-serif"
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            family: "'Inter', sans-serif"
                        }
                    }
                }
            },
            elements: {
                line: {
                    tension: 0.4
                }
            }
        };
    } else if (chartType === 'pie' || chartType === 'doughnut') {
        specificOptions = {
            cutout: chartType === 'doughnut' ? '70%' : '0'
        };
    }
    
    // Create the chart
    new Chart(ctx, {
        type: chartType,
        data: chartData,
        options: { ...animationOptions, ...specificOptions }
    });
}

/**
 * Initialize scroll animations
 */
function initScrollAnimations() {
    // Only run if IntersectionObserver is supported
    if ('IntersectionObserver' in window) {
        const elements = document.querySelectorAll('.animate-on-scroll');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('slide-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1
        });
        
        elements.forEach(element => {
            observer.observe(element);
        });
    }
}

/**
 * Initialize loading state handlers for forms and buttons
 */
function initLoadingStates() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...';
                
                // Re-enable after timeout in case of errors
                setTimeout(() => {
                    if (submitBtn.disabled) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }
                }, 10000);
            }
        });
    });
}

/**
 * Initialize task ID validation
 */
function initTaskValidation() {
    const taskIdInput = document.getElementById('task_id');
    
    if (taskIdInput) {
        taskIdInput.addEventListener('input', function() {
            validateTaskId(this);
        });
        
        taskIdInput.addEventListener('blur', function() {
            validateTaskId(this, true);
        });
    }
}

/**
 * Validate task ID input
 */
function validateTaskId(input, showError = false) {
    const value = input.value.trim();
    const errorElement = document.getElementById('task_id_error') || createErrorElement(input);
    
    if (!value) {
        if (showError) {
            errorElement.textContent = 'Task ID is required';
            errorElement.style.display = 'block';
            input.classList.add('is-invalid');
        }
        return false;
    } else if (isNaN(value) || parseInt(value) <= 0) {
        if (showError) {
            errorElement.textContent = 'Task ID must be a positive number';
            errorElement.style.display = 'block';
            input.classList.add('is-invalid');
        }
        return false;
    } else {
        errorElement.style.display = 'none';
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        return true;
    }
}

/**
 * Create error element for form validation
 */
function createErrorElement(input) {
    const errorElement = document.createElement('div');
    errorElement.id = 'task_id_error';
    errorElement.className = 'invalid-feedback';
    input.parentNode.appendChild(errorElement);
    return errorElement;
}
            const taskId = this.value;
            if (taskId) {
                try {
                    const response = await fetch(`/api/task/${taskId}`);
                    const data = await response.json();
                    
                    if (!data.error) {
                        this.classList.add('is-invalid');
                        const feedback = document.createElement('div');
                        feedback.classList.add('invalid-feedback');
                        feedback.textContent = `Task ID ${taskId} already exists. Please use a different ID.`;
                        this.parentNode.appendChild(feedback);
                    } else {
                        this.classList.remove('is-invalid');
                        const feedback = this.parentNode.querySelector('.invalid-feedback');
                        if (feedback) {
                            feedback.remove();
                        }
                    }
                } catch (error) {
                    console.error('Error checking task ID:', error);
                }
            }
        });
    }

    // Analysis type description
    const taskTypeSelect = document.getElementById('task_type');
    if (taskTypeSelect) {
        const descriptionElement = document.createElement('div');
        descriptionElement.classList.add('form-text', 'mt-2');
        taskTypeSelect.parentNode.appendChild(descriptionElement);
        
        taskTypeSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            const descriptions = {
                'market_analysis': 'Comprehensive analysis of the local real estate market conditions',
                'property_valuation': 'Detailed valuation of a specific property',
                'investment_analysis': 'ROI and financial projections for property investments',
                'neighborhood_insights': 'Analysis of neighborhood characteristics and livability',
                'rental_analysis': 'Rental market analysis and potential rental income',
                'development_potential': 'Assessment of property development or improvement potential'
            };
            
            const description = descriptions[this.value] || '';
            descriptionElement.textContent = description;
        });
    }

    // Auto-refresh for pending tasks
    const taskStatusElement = document.querySelector('.task-status');
    if (taskStatusElement && taskStatusElement.textContent.includes('Pending')) {
        const taskId = taskStatusElement.getAttribute('data-task-id');
        if (taskId) {
            setInterval(async function() {
                try {
                    const response = await fetch(`/api/task/${taskId}`);
                    const data = await response.json();
                    
                    if (data.completed || data.status === 'Completed') {
                        window.location.reload();
                    }
                } catch (error) {
                    console.error('Error checking task status:', error);
                }
            }, 10000); // Check every 10 seconds
        }
    }
});

// Function to copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Show a temporary tooltip
        const tooltip = document.createElement('div');
        tooltip.classList.add('tooltip', 'show');
        tooltip.textContent = 'Copied!';
        document.body.appendChild(tooltip);
        
        // Position the tooltip
        const rect = event.target.getBoundingClientRect();
        tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
        
        // Remove the tooltip after a short delay
        setTimeout(function() {
            tooltip.remove();
        }, 1500);
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
    });
}
