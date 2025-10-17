from flask import Blueprint, render_template, redirect, url_for, session, request
import base64
import math
from datetime import datetime
from db import get_db
from auth import login_required


bp = Blueprint('hist', __name__,)

@bp.route('/history')
@login_required
def view_history():
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE user_id = ?', (session['user_id'],)).fetchone()
    user_id = session['user_id']

    # Filter by date if given
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    search = request.args.get('search', '').lower()
    from_date_display = ''
    to_date_display = ''

    query = 'SELECT batch_id, batch_name, timestamp FROM history WHERE user_id = ?'
    params = [user_id]

    if from_date:
        from_date_display = datetime.strptime(from_date, '%Y-%m-%d').strftime('%d-%m-%Y')
        query += ' AND date(timestamp) >= ?'
        params.append(from_date)
    if to_date:
        to_date_display = datetime.strptime(to_date, '%Y-%m-%d').strftime('%d-%m-%Y')
        query += ' AND date(timestamp) <= ?'
        params.append(to_date)

    query += ' ORDER BY timestamp DESC'
    rows = db.execute(query, params).fetchall()

    # Group by batch
    history_by_batch = {}
    for row in rows:
        if search and search not in row['batch_name'].lower():
            continue
        batch_id = row['batch_id']
        if batch_id not in history_by_batch:
            history_by_batch[batch_id] = {
                'batch_name': row['batch_name'],
                'formatted_ts': datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S.%f').strftime('%d-%m-%Y %H:%M'),
            }

    # Pagination logic
    per_page = 10
    page = int(request.args.get('page', 1))
    total_batches = len(history_by_batch)

    # Avoid ZeroDivisionError
    if total_batches == 0:
        total_pages = 1
        batch_subset = {}
    else:
        total_pages = math.ceil(total_batches / per_page)
        start = (page - 1) * per_page
        end = start + per_page
        batch_subset = dict(list(history_by_batch.items())[start:end])

    return render_template('history.html',
                           user=user,
                           history=batch_subset,
                           current_page=page,
                           total_pages=total_pages,
                           page=request.args.get('page', 1),
                           from_date=request.args.get('from_date', ''),
                           to_date=request.args.get('to_date', ''),
                           search=request.args.get('search', ''),
                           from_date_display=from_date_display,
                           to_date_display=to_date_display)


@bp.route('/history/<batch_id>')
@login_required
def batch_detail(batch_id):
    db = get_db()
    user = db.execute('SELECT * FROM user WHERE user_id = ?', (session['user_id'],)).fetchone()
    user_id = session['user_id']

    rows = db.execute(
        '''SELECT batch_name, image_name, pred_result, timestamp, pred_image
           FROM history
           WHERE user_id = ? AND batch_id = ?''',
        (user_id, batch_id)
    ).fetchall()

    if not rows:
        return redirect('/history')

    entries = [{
        'image_name': row['image_name'],
        'result': row['pred_result'],
        'image_base64': base64.b64encode(row['pred_image']).decode('utf-8')
    } for row in rows]

    batch_detail = {
        'batch_name': rows[0]['batch_name'],
        'formatted_ts': datetime.strptime(rows[0]['timestamp'], '%Y-%m-%d %H:%M:%S.%f').strftime('%d-%m-%Y %H:%M'),
        'entries': entries
    }

    return render_template('history.html',
                           user=user,
                           batch_detail=batch_detail,
                           batch_id=batch_id,
                           page=request.args.get('page', 1),
                           from_date=request.args.get('from_date', ''),
                           to_date=request.args.get('to_date', ''),
                           search=request.args.get('search', ''))


@bp.route('/history/rename/<batch_id>', methods=['POST'])
@login_required
def rename_batch(batch_id):
    db = get_db()
    user_id = session['user_id']
    new_name = request.form['new_name']

    db.execute('UPDATE history SET batch_name = ? WHERE user_id = ? AND batch_id = ?', (new_name, user_id, batch_id))
    db.commit()

    return redirect(url_for('hist.batch_detail', 
                            batch_id=batch_id,
                            search=request.form.get('search', ''),
                            from_date=request.form.get('from_date', ''),
                            to_date=request.form.get('to_date', ''),
                            page=request.form.get('page', 1)))


@bp.route('/history/delete/<batch_id>', methods=['POST'])
@login_required
def delete_batch(batch_id):
    db = get_db()
    user_id = session['user_id']

    db.execute('DELETE FROM history WHERE user_id = ? AND batch_id = ?', (user_id, batch_id))
    db.commit()

    return redirect(url_for('hist.view_history',
                            search=request.form.get('search', ''),
                            from_date=request.form.get('from_date', ''),
                            to_date=request.form.get('to_date', ''),
                            page=request.form.get('page', 1)))
