# TODO(mingjia): market-category prompt.
#
# Names the analyst-standard product category this company sells into, which is then
# used to fetch category-scoped TAM evidence. The distinction that matters: this must
# be THIS company's market (e.g. "IT service management (ITSM) software"), never the
# fund thesis's sector (e.g. "AI infra") — sizing the thesis instead of the company is
# the category error the company-scoped queries were originally guarding against.
#
# Until this file has non-comment content, app/diligence/pipeline.py falls back to
# _CATEGORY_DEFAULT.
