// worxboard site data: manifest.json (written by site/build_site.py) and layout.json, fetched once and
// shared by page.js and viewer.js.
const get = (f) => fetch(f).then((r) => {
  if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`);
  return r.json();
});

export const [manifest, lay] = await Promise.all([get("manifest.json"), get("layout.json")]);
