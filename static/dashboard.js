// Hàm vẽ đồ thị Progress
function renderChart(progressValue) {
    const ctx = document.getElementById('progressChart').getContext('2d');
    
    // Đảm bảo giá trị còn lại không bị âm
    const remaining = 100 - progressValue < 0 ? 0 : 100 - progressValue;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Đã hoàn thành', 'Còn lại'],
            datasets: [{
                data: [progressValue, remaining],
                backgroundColor: ['#6366f1', 'rgba(255,255,255,0.05)'],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            cutout: '85%',
            plugins: {
                legend: { display: false }
            }
        }
    });
}