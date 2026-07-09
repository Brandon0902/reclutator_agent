def eliminar_archivo(storage, nombre: str) -> None:
    if nombre and storage.exists(nombre): storage.delete(nombre)
