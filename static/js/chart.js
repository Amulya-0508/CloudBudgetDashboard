// Dark Mode Chart.js configurations and helpers

function initPieChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Premium color palette for cloud services
    const colors = [
        '#3b82f6', // Compute / Blue
        '#10b981', // Storage / Green
        '#f59e0b', // Database / Yellow
        '#8b5cf6', // Networking / Purple
        '#ec4899', // Serverless / Pink
        '#6b7280', // Other / Gray
    ];
    
    const borderColors = colors.map(color => color + '99');
    
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: 'rgba(17, 24, 39, 0.8)',
                borderWidth: 2,
                hoverOffset: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#9ca3af',
                        font: {
                            family: "'Outfit', sans-serif",
                            size: 12
                        },
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed !== null) {
                                label += '₹' + context.parsed.toLocaleString('en-IN', { minimumFractionDigits: 2 });
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

function initLineChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Create subtle gradient fill under the line
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Monthly Expenses',
                data: data,
                borderColor: '#3b82f6',
                borderWidth: 3,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: 'rgba(17, 24, 39, 0.8)',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        borderColor: 'rgba(255, 255, 255, 0.08)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            family: "'Outfit', sans-serif"
                        }
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        borderColor: 'rgba(255, 255, 255, 0.08)'
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            family: "'Outfit', sans-serif"
                        },
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += '₹' + context.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2 });
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}
