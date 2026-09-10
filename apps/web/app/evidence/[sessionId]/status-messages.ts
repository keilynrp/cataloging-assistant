export const EXTRACT_MESSAGES: Record<string, string> = {
  saved: "La extracción determinista quedó congelada como evidencia local.",
  stale: "El registro DSpace cambió desde la captura. Reabre una sesión con la versión vigente.",
  error: "No fue posible extraer candidatos.",
  unavailable: "La extracción está deshabilitada porque falta la configuración segura.",
};

export const PDF_MESSAGES: Record<string, string> = {
  saved: "El PDF quedó capturado como fuente de evidencia local.",
  too_large: "El PDF supera el máximo permitido de 25 MB.",
  invalid_type: "Sólo se aceptan archivos application/pdf con extensión .pdf.",
  rejected: "El PDF no pudo procesarse (cifrado, corrupto o no es un PDF real).",
  stale: "El registro DSpace cambió desde la captura. Reabre una sesión con la versión vigente.",
  invalid: "Verifica el catalogador y selecciona un archivo PDF antes de enviar.",
  error: "No fue posible subir el PDF.",
  unavailable: "La subida está deshabilitada porque falta la configuración segura.",
};

export const REMOTE_MESSAGES: Record<string, string> = {
  saved: "La URL se obtuvo desde el backend y quedó capturada como fuente de evidencia local.",
  disabled: "El fetch remoto está deshabilitado en esta instalación (EVIDENCE_REMOTE_FETCH_ENABLED).",
  too_large: "El contenido remoto supera el tamaño máximo permitido.",
  stale: "El registro DSpace cambió desde la captura. Reabre una sesión con la versión vigente.",
  invalid: "Verifica el catalogador y escribe una URL http/https antes de enviar.",
  remote_url_invalid: "La URL no es válida (esquema, usuario/contraseña en la URL, host o puerto).",
  remote_target_not_public: "El destino resuelve a una dirección de red no pública.",
  remote_dns_resolution_failed: "No fue posible resolver el nombre de dominio.",
  remote_redirect_blocked: "Se detectó un bucle de redirecciones.",
  remote_redirect_limit: "La URL redirige más veces de las permitidas.",
  remote_content_type_not_allowed: "El tipo de contenido remoto no está permitido.",
  remote_content_invalid: "El contenido remoto no pudo decodificarse como se esperaba.",
  remote_pdf_invalid: "El PDF remoto no pudo procesarse (cifrado, corrupto o no es un PDF real).",
  remote_pdf_timeout: "La extracción del PDF remoto excedió el tiempo máximo configurado.",
  remote_fetch_timeout: "La solicitud remota excedió el tiempo máximo configurado.",
  remote_upstream_error: "El servidor remoto falló o no respondió.",
  rejected: "No fue posible obtener el contenido remoto.",
  error: "No fue posible obtener la evidencia remota.",
  unavailable: "El fetch remoto está deshabilitado porque falta la configuración segura.",
};

export const EXTRACTION_STATUS_LABELS: Record<string, string> = {
  extracted: "Texto extraído",
  no_extractable_text: "Sin texto útil (requiere OCR, no soportado)",
  pending: "Pendiente",
  rejected: "Rechazado",
};

export const COPY_MESSAGES: Record<string, string> = {
  saved: "Los candidatos seleccionados se copiaron a una revisión del borrador local.",
  conflict: "El borrador o el registro fuente cambió. Recarga antes de continuar.",
  invalid: "Algún candidato no es copiable al borrador lingüístico o no supera la validación.",
  error: "No fue posible copiar los candidatos al borrador.",
  unavailable: "La copia está deshabilitada porque falta la configuración segura.",
};
