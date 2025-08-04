// API Testing Functions

async function testImageValidation() {
    const textarea = document.getElementById('imageUrls');
    const resultDiv = document.getElementById('validationResult');
    
    const urls = textarea.value.split('\n').filter(url => url.trim() !== '');
    
    if (urls.length === 0) {
        resultDiv.innerHTML = '<div class="alert alert-warning">Please enter at least one image URL</div>';
        return;
    }
    
    resultDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin"></i> Testing image validation...</div>';
    
    try {
        const response = await fetch('/api/v1/test-image-validation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ urls: urls })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            let html = '<div class="alert alert-success"><h6><i class="fas fa-check-circle"></i> Validation Results</h6>';
            
            html += `<p><strong>Total URLs:</strong> ${urls.length}</p>`;
            html += `<p><strong>Valid URLs:</strong> ${data.valid_urls.length}</p>`;
            html += `<p><strong>Unreachable URLs:</strong> ${data.unreachable_urls.length}</p>`;
            html += `<p><strong>Threshold Met:</strong> ${data.threshold_met ? 'Yes' : 'No'}</p>`;
            
            if (data.valid_urls.length > 0) {
                html += '<h6 class="mt-3">Valid URLs:</h6><ul>';
                data.valid_urls.forEach(url => {
                    html += `<li class="text-success"><i class="fas fa-check"></i> ${url}</li>`;
                });
                html += '</ul>';
            }
            
            if (data.unreachable_urls.length > 0) {
                html += '<h6 class="mt-3">Unreachable URLs:</h6><ul>';
                data.unreachable_urls.forEach(url => {
                    html += `<li class="text-danger"><i class="fas fa-times"></i> ${url}</li>`;
                });
                html += '</ul>';
            }
            
            html += '</div>';
            resultDiv.innerHTML = html;
        } else {
            resultDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> Error: ${data.error || 'Unknown error'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle"></i> Network Error: ${error.message}</div>`;
    }
}

async function checkHealth() {
    const resultDiv = document.getElementById('healthResult');
    
    resultDiv.innerHTML = '<div class="alert alert-info"><i class="fas fa-spinner fa-spin"></i> Checking service health...</div>';
    
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        if (response.ok) {
            resultDiv.innerHTML = `<div class="alert alert-success">
                <h6><i class="fas fa-check-circle"></i> Service Healthy</h6>
                <p><strong>Status:</strong> ${data.status}</p>
                <p><strong>Service:</strong> ${data.service}</p>
            </div>`;
        } else {
            resultDiv.innerHTML = `<div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> Service Unhealthy: ${data.error || 'Unknown error'}
            </div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle"></i> Health Check Failed: ${error.message}
        </div>`;
    }
}

// Smooth scrolling for navigation links
document.addEventListener('DOMContentLoaded', function() {
    // Add click handlers to nav links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Update active nav link on scroll
    const navLinks = document.querySelectorAll('.nav-pills .nav-link');
    const sections = document.querySelectorAll('section[id]');
    
    function updateActiveNav() {
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (window.scrollY >= sectionTop - 100) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === '#' + current) {
                link.classList.add('active');
            }
        });
    }
    
    window.addEventListener('scroll', updateActiveNav);
    updateActiveNav(); // Initial call
});

// Copy code to clipboard functionality
function addCopyButtons() {
    document.querySelectorAll('pre code').forEach(block => {
        const button = document.createElement('button');
        button.className = 'btn btn-sm btn-outline-secondary position-absolute top-0 end-0 m-2';
        button.innerHTML = '<i class="fas fa-copy"></i>';
        button.onclick = () => {
            navigator.clipboard.writeText(block.textContent).then(() => {
                button.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    button.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            });
        };
        
        const pre = block.parentElement;
        pre.style.position = 'relative';
        pre.appendChild(button);
    });
}

// Add copy buttons after DOM is loaded
document.addEventListener('DOMContentLoaded', addCopyButtons);
