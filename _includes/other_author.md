<h1 id="other_author"></h1>

<div class="publications-intro">
  <h2>Other Author</h2>
  <p>
    <a href="https://scholar.google.com/citations?user=bbGBlQ0AAAAJ&hl=en&oi=ao" target="_blank" rel="noopener">Google Scholar</a>
    <span aria-hidden="true">·</span>
    <a href="https://www.researchgate.net/profile/Yanshang-Wang" target="_blank" rel="noopener">ResearchGate</a>
  </p>
</div>

<div class="publications">
  <ol class="bibliography publication-list">
    {% for link in site.data.other_author.main %}
    <li class="publication-item">
      <article class="publication-card">
        <div class="publication-card__meta">
          {% if link.conference %}
          <span class="publication-venue">{{ link.conference }}</span>
          {% endif %}
          {% if link.notes %}
          <span class="publication-status">{{ link.notes }}</span>
          {% endif %}
        </div>

        <h3 class="publication-title">
          {% if link.page %}
          <a href="{{ link.page }}" target="_blank" rel="noopener">{{ link.title }}</a>
          {% elsif link.pdf %}
          <a href="{{ link.pdf }}" target="_blank" rel="noopener">{{ link.title }}</a>
          {% else %}
          {{ link.title }}
          {% endif %}
        </h3>

        <div class="publication-authors">{{ link.authors }}</div>

      </article>
    </li>
    {% endfor %}
  </ol>
</div>
