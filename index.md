# My Crypto Dashboard

## Live Prices
<div id="price-table">Loading prices…</div>

<script>
  async function fetchPrices() {
    const res = await fetch(
      'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd'
    );
    const data = await res.json();
    let html = '<table><tr><th>Coin</th><th>USD</th></tr>';
    for (let [coin, vals] of Object.entries(data)) {
      html += `<tr><td>${coin}</td><td>$${vals.usd.toLocaleString()}</td></tr>`;
    }
    document.getElementById('price-table').innerHTML = html;
  }
  fetchPrices();
  setInterval(fetchPrices, 60_000);
</script>

