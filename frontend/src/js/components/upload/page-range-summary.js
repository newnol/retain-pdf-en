class PageRangeSummary extends HTMLElement {
  connectedCallback() {
    this.classList.add("page-range-summary");
    if (!this.textContent.trim()) {
      this.textContent = "Selected pages: -";
    }
    if (!this.classList.contains("hidden") && this.textContent.includes("Selected pages: -")) {
      this.classList.add("hidden");
    }
  }
}

if (!customElements.get("page-range-summary")) {
  customElements.define("page-range-summary", PageRangeSummary);
}
