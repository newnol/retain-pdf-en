async function loadPartial(relativePath) {
  const url = new URL(relativePath, import.meta.url);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load page partial: ${relativePath}`);
  }
  return response.text();
}

export async function renderPageShell() {
  const [mainContent, dialogs] = await Promise.all([
    loadPartial("../partials/main-content.html"),
    loadPartial("../partials/dialogs.html"),
  ]);

  document.body.innerHTML = `${mainContent}${dialogs}`;
}
