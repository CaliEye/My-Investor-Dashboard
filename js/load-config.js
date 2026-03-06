/**
* load-config.js
* Loads config/lindy_config.json and sets window.LINDY_CONFIG
* This file must be loaded BEFORE signal-tally.js and lindy-alerts.js
* 
* SECURITY: config/lindy_config.json is in .gitignore — never committed to repo.
* For GitHub Pages, this fetch will 404 in production (expected).
* PAT is only active when running locally via Live Server or similar.
*/

(async function () {
 try {
   const res = await fetch('./config/lindy_config.json', { cache: 'no-store' });
   if (res.ok) {
     const cfg = await res.json();
     window.LINDY_CONFIG = cfg;
     console.log('[Config] lindy_config.json loaded — PAT active, GitHub patch enabled');
   } else {
     console.warn('[Config] lindy_config.json not found (status:', res.status, ') — GitHub patch disabled. Running in read-only mode.');
     window.LINDY_CONFIG = { github_pat: '', webhook_url: '' };
   }
 } catch (e) {
   console.warn('[Config] Could not load lindy_config.json:', e.message, '— running in read-only mode.');
   window.LINDY_CONFIG = { github_pat: '', webhook_url: '' };
 }
})();