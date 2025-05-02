let currentPage = 1;
const pageSize = 10;

document.getElementById('searchForm').addEventListener('submit', async function (event) {
    event.preventDefault();
    currentPage = 1;  // Reset to the first page for new queries
    fetchSearchResults();
});

async function fetchSearchResults() {
    const query = document.getElementById('queryInput').value.trim();
    const resultsContainer = document.getElementById('resultsContainer');

    if (query) {
        resultsContainer.innerHTML = `<div class="loading">Searching...</div>`;
        try {
            const response = await fetch(`http://127.0.0.1:5000/search?query=${encodeURIComponent(query)}&page=${currentPage}&size=${pageSize}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();

            if (data.results && data.results.length > 0) {
                const resultsHTML = data.results.map(result => `
                    <div class="result-item">
                        <h3><a href="${result.url}" target="_blank">${result.title}</a></h3>
                        <p><strong>Source ID:</strong> ${result.source_id}</p>
                        <p><strong>Published:</strong> ${result.published}</p>
                        <p>${result.content}</p>
                    </div>
                `).join('');
                resultsContainer.innerHTML = resultsHTML;

                // Add pagination controls
                resultsContainer.innerHTML += `
                    <div class="pagination-controls">
                        ${currentPage > 1 ? `<button id="prevPage">Previous</button>` : ''}
                        <button id="nextPage">Next</button>
                    </div>
                `;

                // Add event listeners to pagination buttons
                if (currentPage > 1) {
                    document.getElementById('prevPage').addEventListener('click', () => {
                        currentPage--;
                        fetchSearchResults();
                    });
                }
                document.getElementById('nextPage').addEventListener('click', () => {
                    currentPage++;
                    fetchSearchResults();
                });
            } else {
                resultsContainer.innerHTML = `<div class="no-results">No results found for "${query}".</div>`;
            }
        } catch (error) {
            console.error('Error fetching search results:', error);
            resultsContainer.innerHTML = `<div class="error">An error occurred. Please try again later.</div>`;
        }
    } else {
        resultsContainer.innerHTML = `<div class="error">Please enter a valid query.</div>`;
    }
}
