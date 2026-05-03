use crate::db::Db;
use crate::error::AppError;
use crate::models::{
    glossary_to_detail, glossary_to_summary, GlossaryCsvParseInput, GlossaryCsvParseView,
    GlossaryDetailView, GlossaryListView, GlossaryUpsertInput,
};
use crate::services::glossaries::{
    create_glossary, delete_glossary, list_glossaries, load_glossary_or_404, parse_glossary_csv,
    update_glossary,
};

pub fn create_glossary_view(
    db: &Db,
    payload: &GlossaryUpsertInput,
) -> Result<GlossaryDetailView, AppError> {
    let record = create_glossary(db, payload)?;
    Ok(glossary_to_detail(&record))
}

pub fn list_glossaries_view(db: &Db) -> Result<GlossaryListView, AppError> {
    let items = list_glossaries(db)?
        .iter()
        .map(glossary_to_summary)
        .collect();
    Ok(GlossaryListView { items })
}

pub fn get_glossary_view(db: &Db, glossary_id: &str) -> Result<GlossaryDetailView, AppError> {
    let record = load_glossary_or_404(db, glossary_id)?;
    Ok(glossary_to_detail(&record))
}

pub fn update_glossary_view(
    db: &Db,
    glossary_id: &str,
    payload: &GlossaryUpsertInput,
) -> Result<GlossaryDetailView, AppError> {
    let record = update_glossary(db, glossary_id, payload)?;
    Ok(glossary_to_detail(&record))
}

pub fn delete_glossary_view(db: &Db, glossary_id: &str) -> Result<GlossaryDetailView, AppError> {
    let record = load_glossary_or_404(db, glossary_id)?;
    delete_glossary(db, glossary_id)?;
    Ok(glossary_to_detail(&record))
}

pub fn parse_glossary_csv_view(
    payload: &GlossaryCsvParseInput,
) -> Result<GlossaryCsvParseView, AppError> {
    let entries = parse_glossary_csv(payload)?;
    Ok(GlossaryCsvParseView {
        entry_count: entries.len(),
        entries,
    })
}
