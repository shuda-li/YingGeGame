(function () {
  var css = getComputedStyle(document.documentElement);
  function tok(name, fallback) {
    var v = css.getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  /* Single active chart palette (Warm Editorial), read once and reused. */
  var chartSeries1 = tok('--chart-series-1', '#B8551D');
  var chartSeries2 = tok('--chart-series-2', '#F59E42');
  var chartOther = tok('--chart-other', '#E4D8CC');
  var axisColor = tok('--chart-axis', '#7A6A5E');
  var labelColor = tok('--chart-label', '#7A6A5E');
  var gridColor = tok('--chart-grid', 'rgba(42, 33, 27, 0.12)');
  var tooltipBg = tok('--chart-tooltip-bg', '#FFFFFF');
  var inkColor = tok('--ink', '#2A211B');
  var borderColor = tok('--page-border', '#E4D8CC');

  var el = document.getElementById('chart-difficulty');
  if (!el) return;

  function emptyState(node, message) {
    node.innerHTML =
      '<div style="height:100%;display:flex;align-items:center;justify-content:center;' +
      'color:' + labelColor + ';font-size:13px;border:1px dashed ' + borderColor +
      ';border-radius:12px;">' + message + '</div>';
  }

  if (typeof echarts === 'undefined') {
    emptyState(el, '图表库未加载，暂无法渲染');
    return;
  }

  var stages = ['第1关', '第2关', '第3关', '第4关', '第5关', '第6关',
    '第7关', '第8关', '第9关', '第10关', '第11关', '第12关'];
  var difficulty = [10, 16, 22, 30, 36, 45, 52, 60, 68, 76, 85, 95];
  var ability = [8, 15, 24, 32, 40, 48, 55, 63, 70, 79, 86, 94];

  var chart = echarts.init(el, null, { renderer: 'svg' });
  chart.setOption({
    animation: false,
    color: [chartSeries1, chartSeries2],
    grid: { left: 8, right: 16, top: 64, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      appendToBody: true,
      backgroundColor: tooltipBg,
      borderColor: borderColor,
      textStyle: { color: inkColor, fontSize: 12 },
      axisPointer: { type: 'line', lineStyle: { color: chartOther } }
    },
    legend: {
      top: 8,
      left: 0,
      icon: 'roundRect',
      itemWidth: 12,
      itemHeight: 12,
      itemGap: 20,
      textStyle: { color: labelColor, fontSize: 12 }
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: stages,
      axisLine: { lineStyle: { color: chartOther } },
      axisTick: { show: false },
      axisLabel: { color: axisColor, fontSize: 11, interval: 0 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      name: '难度 / 能力值',
      nameTextStyle: { color: labelColor, fontSize: 11, align: 'left' },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: axisColor, fontSize: 11 },
      splitLine: { lineStyle: { color: gridColor, width: 1 } }
    },
    series: [
      {
        name: '关卡难度',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: chartSeries1 },
        itemStyle: { color: chartSeries1 },
        data: difficulty,
        markPoint: {
          symbol: 'pin',
          symbolSize: 40,
          itemStyle: { color: chartSeries1 },
          label: { color: '#FFFFFF', fontSize: 10 },
          data: [
            { name: '能力跃迁', coord: [3, 30], value: '跃迁' },
            { name: '能力跃迁', coord: [7, 60], value: '跃迁' }
          ]
        }
      },
      {
        name: '玩家能力',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 2, color: chartSeries2 },
        itemStyle: { color: chartSeries2 },
        data: ability
      }
    ]
  });

  window.addEventListener('resize', function () {
    chart.resize();
  });
})();