with engine.connect() as conn_local:
    pass

with engine.connect() as conn_local:
    sql_text = ('INSERT INTO beringung.feedback (zeitstempel, name, kontaktaufnahme, mail, text, '
                'verbesserung, rating) VALUES (:zeitstempel, :name, :kontaktaufnahme, :email, :feedbacktext, '
                ':verbesserung, :rating)')
    values = {
        'zeitstempel': zeitstempel,
        'name': name,
        'kontaktaufnahme': kontaktaufnahme,
        'email': email,
        'feedbacktext': feedbacktext,
        'verbesserung': verbesserung,
        'rating': rating,
    }
    conn_local.execute(sa.text(sql_text), [values])
    conn_local.commit()

with engine.connect() as conn_local:
    conn_local.execute(sa.text(sql_text), [values])
    conn_local.commit()