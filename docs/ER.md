# Entity-Relationship Diagram — Kelp Nexus

```mermaid
erDiagram
  users ||--o{ reports : authors
  users ||--o{ comments : writes
  users ||--o{ favorites : has
  users ||--o{ recently_viewed : has
  users ||--o{ report_views : generates
  users ||--o{ audit_log : actor

  categories ||--o{ reports : categorizes
  categories ||--o{ categories : parent

  reports ||--o{ report_versions : has
  reports ||--o{ comments : has
  reports ||--o{ favorites : favorited_in
  reports ||--o{ recently_viewed : seen_in
  reports ||--o{ report_views : viewed_in
  reports ||--o{ embeddings : chunked_into
  reports }o--o{ tags : tagged
  reports }o--o{ technologies : uses

  comments ||--o{ comments : replies

  users {
    uuid id PK
    string azure_oid
    string email UK
    string hashed_password
    string name
    enum role
    string team
    string department
    string title
    text bio
    bool is_active
    timestamptz created_at
  }

  reports {
    uuid id PK
    string title
    string slug UK
    text description
    text summary
    text content_text
    uuid author_id FK
    string team
    string department
    uuid category_id FK
    string project
    enum status
    enum visibility
    int current_version
    string github_repo
    string pull_request
    string demo_url
    string video_url
    int view_count
    tsvector search_vector
    timestamptz created_at
    timestamptz updated_at
  }

  report_versions {
    uuid id PK
    uuid report_id FK
    int version
    string html_blob_path
    string pdf_blob_path
    text extracted_text
    text changelog
    uuid created_by FK
    timestamptz created_at
  }

  categories {
    uuid id PK
    string name
    string slug UK
    text description
    uuid parent_id FK
  }

  tags {
    uuid id PK
    string name
    string slug UK
  }

  technologies {
    uuid id PK
    string name
    string slug UK
  }

  comments {
    uuid id PK
    uuid report_id FK
    uuid author_id FK
    uuid parent_id FK
    text body
    timestamptz created_at
  }

  favorites {
    uuid id PK
    uuid user_id FK
    uuid report_id FK
    timestamptz created_at
  }

  recently_viewed {
    uuid id PK
    uuid user_id FK
    uuid report_id FK
    timestamptz viewed_at
  }

  report_views {
    uuid id PK
    uuid report_id FK
    uuid user_id FK
    timestamptz viewed_at
  }

  embeddings {
    uuid id PK
    uuid report_id FK
    int chunk_index
    text content
    vector embedding
  }

  audit_log {
    uuid id PK
    uuid actor_id FK
    string action
    string entity_type
    string entity_id
    text detail
    timestamptz created_at
  }
```

## Indexes & constraints

- `reports.slug`, `categories.slug`, `tags.slug`, `technologies.slug` — unique.
- `reports.search_vector` — GIN index (`ix_reports_search_vector`).
- `embeddings.embedding` — ivfflat cosine index (`ix_embeddings_vector`).
- `report_versions(report_id, version)` — unique.
- `favorites(user_id, report_id)` & `recently_viewed(user_id, report_id)` — unique.
- `report_views.viewed_at` — indexed for trending/analytics windows.
