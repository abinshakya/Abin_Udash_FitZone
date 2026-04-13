document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mainContent = document.getElementById('main-content');

    // Sidebar Toggle
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            if (window.innerWidth > 1024) {
                sidebar.classList.toggle('collapsed');
            } else {
                sidebar.classList.toggle('active');
            }
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 1024) {
            if (!sidebar.contains(event.target) && !sidebarToggle.contains(event.target) && sidebar.classList.contains('active')) {
                sidebar.classList.remove('active');
            }
        }
    });

    // Add icons to dashboard cards (if not already handled by templates)
    const appIcons = {
        'auth': 'fa-users-cog',
        'login_logout_register': 'fa-user-plus',
        'membership': 'fa-id-card',
        'payment': 'fa-credit-card',
        'trainer': 'fa-dumbbell',
        'notifications': 'fa-bell',
        'chat': 'fa-comments',
        'fitness_plan': 'fa-calendar-alt',
        'Ai_chatbot': 'fa-robot',
        'food_recommendation_system': 'fa-utensils',
    };

    // Sidebar Group Toggle (Apps/Models)
    const groupTitles = document.querySelectorAll('.group-title');
    groupTitles.forEach(title => {
        title.addEventListener('click', function() {
            const group = this.parentElement;
            const items = group.querySelector('.group-items');
            const icon = this.querySelector('.group-arrow');
            
            if (items.style.display === 'none' || items.style.display === '') {
                // Close other groups first (accordion style)
                document.querySelectorAll('.group-items').forEach(el => el.style.display = 'none');
                document.querySelectorAll('.group-arrow').forEach(el => el.style.transform = 'rotate(0deg)');
                
                items.style.display = 'block';
                if (icon) icon.style.transform = 'rotate(90deg)';
                this.classList.add('active');
            } else {
                items.style.display = 'none';
                if (icon) icon.style.transform = 'rotate(0deg)';
                this.classList.remove('active');
            }
        });
    });

    // Auto-open group if a model inside it is active
    document.querySelectorAll('.group-items a.active').forEach(activeLink => {
        const group = activeLink.closest('.sidebar-group');
        if (group) {
            const items = group.querySelector('.group-items');
            const title = group.querySelector('.group-title');
            const icon = title.querySelector('.group-arrow');
            items.style.display = 'block';
            if (icon) icon.style.transform = 'rotate(90deg)';
            title.classList.add('active');
        }
    });

    // Dashboard Analytics Charts
    function initDashboardCharts() {
        if (typeof ApexCharts === 'undefined') {
            console.error('ApexCharts library not loaded.');
            return;
        }

        const primaryColor = '#f97316';
        const secondaryColor = '#000000';
        const chartColors = ['#f97316', '#000000', '#64748b', '#94a3b8', '#cbd5e1'];

        function safeRender(selector, options) {
            try {
                const el = document.getElementById(selector);
                if (!el) return;
                
                const labels = JSON.parse(el.dataset.labels || '[]');
                const series = JSON.parse(el.dataset.series || '[]');
                
                if (series.length === 0 || (Array.isArray(series[0]) && series[0].length === 0)) {
                    el.innerHTML = '<div style="display:flex; align-items:center; justify-content:center; height:100%; color:#94a3b8;">No data available yet</div>';
                    return;
                }

                // Inject data into options
                if (options.chart.type === 'pie' || options.chart.type === 'donut') {
                    options.series = series;
                    options.labels = labels;
                } else {
                    options.series[0].data = series;
                    options.xaxis = options.xaxis || {};
                    options.xaxis.categories = labels;
                }

                new ApexCharts(el, options).render();
            } catch (err) {
                console.error('Error rendering chart ' + selector + ':', err);
            }
        }

        // 1. User Growth Chart (Bar)
        safeRender('userGrowthChart', {
            chart: { type: 'bar', height: 300, toolbar: { show: false } },
            series: [{ name: 'New Users', data: [] }],
            colors: [primaryColor],
            plotOptions: { bar: { borderRadius: 4, columnWidth: '50%' } },
            dataLabels: { enabled: false }
        });

        // 2. Revenue Chart (Area)
        safeRender('revenueChart', {
            chart: { type: 'area', height: 300, toolbar: { show: false } },
            series: [{ name: 'Revenue', data: [] }],
            colors: [primaryColor],
            stroke: { curve: 'smooth', width: 2 },
            fill: {
                type: 'gradient',
                gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.1, stops: [0, 90, 100] }
            },
            dataLabels: { enabled: false }
        });

        // 3. Membership Chart (Donut)
        safeRender('membershipChart', {
            chart: { type: 'donut', height: 300 },
            colors: chartColors,
            legend: { position: 'bottom' },
            plotOptions: { pie: { donut: { size: '70%', labels: { show: true, total: { show: true, label: 'Plans' } } } } }
        });

        // 4. Booking Chart (Pie)
        safeRender('bookingChart', {
            chart: { type: 'pie', height: 300 },
            colors: chartColors,
            legend: { position: 'bottom' }
        });
    }

    initDashboardCharts();
});
