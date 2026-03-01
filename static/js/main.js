// Update the form submission part in main.js
// Look for this section and replace it:

// Form submission
if (generateForm) {
    generateForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        console.log('📝 Form submitted');
        
        const prompt = promptTextarea ? promptTextarea.value.trim() : '';
        
        if (!prompt) {
            showStatus('Please enter a prompt', 'error');
            return;
        }

        console.log('🎨 Generating image for:', prompt);

        // Disable form
        if (generateBtn) {
            generateBtn.disabled = true;
            const btnText = generateBtn.querySelector('.btn-text');
            const btnLoader = generateBtn.querySelector('.btn-loader');
            if (btnText) btnText.textContent = 'Generating...';
            if (btnLoader) btnLoader.style.display = 'inline-block';
        }

        // Update UI
        if (outputStatus) {
            outputStatus.textContent = '🎨 Generating...';
            outputStatus.className = 'output-status generating';
        }
        
        if (genTime) genTime.textContent = '⏱️ Generating... (may take 1-2 minutes)';
        
        // Hide previous image
        if (generatedImage) generatedImage.style.display = 'none';
        if (imagePlaceholder) {
            imagePlaceholder.style.display = 'flex';
            imagePlaceholder.innerHTML = `
                <div class="loader" style="text-align: center;">
                    <div class="cyber-spinner" style="width: 50px; height: 50px; border: 3px solid transparent; border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto;"></div>
                    <p style="color: var(--primary); margin-top: 1rem;">Generating your image...</p>
                    <p style="color: var(--text-secondary); font-size: 0.9rem;">This may take 1-2 minutes</p>
                </div>
            `;
        }
        
        // Show loading overlay
        if (loadingOverlay) loadingOverlay.style.display = 'flex';

        const startTime = Date.now();

        try {
            // Create abort controller for timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 second timeout

            // Make API request
            console.log('📡 Sending request to /api/generate');
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt: prompt }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            console.log('📡 Response status:', response.status);
            
            if (!response.ok) {
                let errorMessage;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || `HTTP error! status: ${response.status}`;
                } catch {
                    errorMessage = `HTTP error! status: ${response.status}`;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            console.log('📡 Response data:', data);

            if (data.success && data.image_url) {
                // Display the generated image
                if (generatedImage && imagePlaceholder) {
                    // Preload image
                    const img = new Image();
                    img.onload = function() {
                        generatedImage.src = data.image_url;
                        imagePlaceholder.style.display = 'none';
                        generatedImage.style.display = 'block';
                        
                        // Update status
                        if (outputStatus) {
                            outputStatus.textContent = '✅ Generation Complete!';
                            outputStatus.className = 'output-status complete';
                        }
                        
                        // Enable download button
                        if (downloadBtn) {
                            downloadBtn.style.display = 'inline-flex';
                            downloadBtn.disabled = false;
                        }
                        
                        // Calculate time
                        const endTime = Date.now();
                        const timeTaken = ((endTime - startTime) / 1000).toFixed(1);
                        if (genTime) genTime.textContent = `⏱️ Generated in ${timeTaken} seconds`;
                        
                        // Hide loading overlay
                        if (loadingOverlay) loadingOverlay.style.display = 'none';
                    };
                    
                    img.onerror = function() {
                        throw new Error('Failed to load image');
                    };
                    
                    img.src = data.image_url;
                }
            } else {
                throw new Error(data.error || 'Generation failed');
            }
        } catch (error) {
            console.error('❌ Error:', error);
            
            // Check if it's an abort error (timeout)
            if (error.name === 'AbortError') {
                showStatus('❌ Request timeout', 'error');
                if (genTime) genTime.textContent = '⏱️ Request timed out';
                if (imagePlaceholder) {
                    imagePlaceholder.innerHTML = `
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#ff0000" stroke-width="1">
                            <circle cx="12" cy="12" r="10" stroke="#ff0000"/>
                            <line x1="12" y1="8" x2="12" y2="12" stroke="#ff0000"/>
                            <circle cx="12" cy="16" r="1" fill="#ff0000"/>
                        </svg>
                        <p style="color: #ff0000;">Request timed out</p>
                        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.5rem;">The server is taking too long to respond. Please try again.</p>
                    `;
                }
            } else {
                // Show error
                showStatus('❌ Generation failed', 'error');
                
                if (genTime) genTime.textContent = '⏱️ Generation failed';
                
                if (imagePlaceholder) {
                    imagePlaceholder.innerHTML = `
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#ff0000" stroke-width="1">
                            <circle cx="12" cy="12" r="10" stroke="#ff0000"/>
                            <line x1="12" y1="8" x2="12" y2="12" stroke="#ff0000"/>
                            <circle cx="12" cy="16" r="1" fill="#ff0000"/>
                        </svg>
                        <p style="color: #ff0000;">${error.message}</p>
                        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.5rem;">Please try again</p>
                    `;
                }
            }
            
            // Hide loading overlay
            if (loadingOverlay) loadingOverlay.style.display = 'none';
        } finally {
            // Re-enable form
            if (generateBtn) {
                generateBtn.disabled = false;
                const btnText = generateBtn.querySelector('.btn-text');
                const btnLoader = generateBtn.querySelector('.btn-loader');
                if (btnText) btnText.textContent = 'Generate Image';
                if (btnLoader) btnLoader.style.display = 'none';
            }
        }
    });
}