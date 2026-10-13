(function () {
  function markFallback(nodes) {
    Array.prototype.forEach.call(nodes, function (el) {
      el.setAttribute('data-fallback', 'true');
    });
  }

  function render() {
    var nodes = document.querySelectorAll('.mermaid');
    if (!nodes.length) return;

    if (typeof mermaid === 'undefined') {
      markFallback(nodes);
      return;
    }

    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      theme: 'base',
      fontFamily: "'Bricolage Grotesque', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', sans-serif",
      themeVariables: {
        fontSize: '14px',
        background: '#FFFDFA',
        primaryColor: '#FBEEE3',
        primaryTextColor: '#3A2A1E',
        primaryBorderColor: '#B8551D',
        secondaryColor: '#F5DCC8',
        tertiaryColor: '#FBF6F0',
        lineColor: '#8E6E63',
        textColor: '#2A211B',
        mainBkg: '#FBEEE3',
        nodeBorder: '#B8551D',
        clusterBkg: '#FBF6F0',
        clusterBorder: '#E4D8CC',
        edgeLabelBackground: '#FFFDFA',
        titleColor: '#2A211B'
      },
      flowchart: { curve: 'basis', useMaxWidth: true, htmlLabels: true },
      state: { useMaxWidth: true }
    });

    try {
      mermaid.run({ querySelector: '.mermaid' });
    } catch (err) {
      markFallback(nodes);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();