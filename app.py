#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import json
import dateutil.parser
import babel
import sys
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form

from forms import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#
# Creating an unconfigured Flask-SQLAlchemy instance
# we first create an SQLAchemy object and then configure the application later to support it
db = SQLAlchemy()

app = Flask(__name__)
app.config.from_object('config') # connect app to a local postgresql database
moment = Moment(app)
db = SQLAlchemy(app) # initializing the instance with the app context
migrate = Migrate(app, db) # linking flask migrate to our app and database

#tip:https://stackoverflow.com/questions/41828711/flask-blueprint-sqlalchemy-cannot-import-name-db-into-moles-file
from models import Venue, Artist, Show

# db.create_all()

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

# home page route handle
@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

# Venue page route handler
@app.route('/venues')
def venues():
  # get distinct city and state combination
  areas = db.session.query(Venue.city, Venue.state).distinct()
  data = []
  for venue in areas:
    venue = dict(zip(('city', 'state'), venue))
    venue['venues'] = []
    query = db.session.query(Venue).filter_by(city=venue['city'], state= venue['state']).all()
    for venue_data in query:
      upcoming_shows = db.session.query(Show).filter(
        (Show.venue_id == venue_data.id) &
        (Show.start_time > datetime.now().strftime('%Y-%m-%d %H:%S:%M'))
        ).all()
      venues_data = {
        'id': venue_data.id,
        'name': venue_data.name,
        'num_upcoming_shows': len(upcoming_shows)
      }
      venue['venues'].append(venues_data)
    data.append(venue)
  return render_template('pages/venues.html', areas=data);

# venue Search route handle
@app.route('/venues/search', methods=['POST'])
def search_venues():
  # get user search term
  search_term = request.form.get('search_term', '')
  results = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_term}%')).all()
  response = {}
  response['count'] = len(results)
  response['data'] = []
  for result in results:
    venue_data = {}
    venue_data['id'] = result.id
    venue_data['name'] = result.name
    upcoming_shows = db.session.query(Show).filter(
              (Show.venue_id == result.id) &
              (Show.start_time > datetime.now().strftime('%Y-%m-%d %H:%S:%M'))
          ).all()
    venue_data['num_upcoming_shows'] = len(upcoming_shows)
    response['data'].append(venue_data)
  
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

# Route handler for individual venue pages
@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
  data = {}
  data['id'] = venue.id
  data['name'] = venue.name
  data['genres'] = venue.genres
  data['address'] = venue.address
  data['city'] = venue.city
  data['state'] = venue.state
  data['phone'] = venue.phone
  data['website'] = venue.website
  data['facebook_link'] = venue.facebook_link
  data['seeking_talent'] = venue.seeking_talent
  data['seeking_description'] = venue.seeking_description
  data['image_link'] = venue.image_link
  data['past_shows'] = []
  data['upcoming_shows'] = []
  data['past_shows_count'] = 0
  data['upcoming_shows_count'] = 0

  query = db.session.query(Show.artist_id, Artist.name,
              Artist.image_link, Show.start_time)
  query = query.join(Artist)
  shows = query.filter(Show.venue_id == venue_id).all()

  for show in shows:
    showtime = show.start_time.strftime('%Y-%m-%d %H:%S:%M')
    current_time = datetime.now().strftime('%Y-%m-%d %H:%S:%M')
    # past shows
    if showtime < current_time:
      data['past_shows'].append({
        'artist_id': show.artist_id,
        'artist_name': show.name,
        'artist_image_link': show.image_link,
        'start_time': format_datetime(str(show.start_time))
      })
      data['past_shows_count'] = data['past_shows_count'] + 1
    else:
      data['upcoming_shows'].append({
        'artist_id': show.artist_id,
        'artist_name': show.name,
        'artist_image_link': show.image_link,
        'start_time': format_datetime(str(show.start_time))
      })
      data['upcoming_shows_count'] = data['upcoming_shows_count'] + 1 

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

# Get the Create Venue form
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

# Post handler for Venue Creation
@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
    form = VenueForm()
    name = form.name.data
    city = form.city.data
    state = form.state.data
    address = form.address.data
    phone = form.phone.data
    genres = form.genres.data
    facebook_link = form.facebook_link.data
    website = form.website.data
    image_link = form.image_link.data
    if form.seeking_talent.data == 'Yes':
      seeking_talent = True
    else:
      seeking_talent = False
    seeking_description = form.seeking_description.data

    venue = Venue(name=name, city=city,state=state,
        address=address, phone=phone, genres=genres, 
        facebook_link=facebook_link, website=website,
        image_link=image_link, seeking_talent = seeking_talent,
        seeking_description = seeking_description
        )
    db.session.add(venue)
    db.session.commit()
    # on successful db insert, flash success
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occured. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()
  return render_template('pages/home.html')

# route handler for deleting a gien Venue
@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
    name = venue.name
    db.session.delete(venue)
    db.session.commit()
    # on successful db delete, flash success
    flash('Venue ' + name + ' was successfully deleted')
  except:
    db.session.rollback()
    flash('An error occured. Venue ' + name + ' could not be')
  finally:
    db.session.close()
  
  return jsonify({'success': True})

#  Artists
#  ----------------------------------------------------------------

# Route handler for Artists overview page
@app.route('/artists')
def artists():
  artists = db.session.query(Artist).all()
  data = []
  for artist in artists:
    artist_detail = {}
    artist_detail['id'] = artist.id
    artist_detail['name'] = artist.name
    data.append(artist_detail)
   
  return render_template('pages/artists.html', artists=data)

# Artist Search route handler
@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  results = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_term}%')).all()
  response = {}
  response['count'] = len(results)  
  response['data'] = []
  for result in results:
    artist_data = {}
    artist_data['id'] = result.id
    artist_data['name'] = result.name
    upcoming_shows = db.session.query(Show).filter(
      (Show.artist_id == result.id) &
      (Show.start_time > datetime.now().strftime('%Y-%m-%d %H:%S:%M'))
    ).all()
    artist_data['num_upcoming_shows'] = len(upcoming_shows)
    response['data'].append(artist_data)
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

# Route handler for individual artist pages
@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
  data = {}
  data['id'] = artist.id
  data['name'] = artist.name
  data['genres'] = artist.genres
  data['city'] = artist.city
  data['state'] = artist.state
  data['phone'] = artist.phone
  data['website'] = artist.website
  data['facebook_link'] = artist.facebook_link
  data['seeking_venue'] = artist.seeking_venue
  data['seeking_description'] = artist.seeking_description
  data['image_link'] = artist.image_link
  data['past_shows'] = []
  data['upcoming_shows'] = []
  data['past_shows_count'] = 0
  data['upcoming_shows_count'] = 0

  query = db.session.query(Show.venue_id, Venue.name,
                Venue.image_link, Show.start_time)
  query = query.join(Venue)
  shows = query.filter(Show.artist_id == artist_id).all()
  for show in shows:
    showtime = show.start_time.strftime('%Y-%m-%d %H:%S:%M')
    current_time = datetime.now().strftime('%Y-%m-%d %H:%S:%M')
    # past shows
    if showtime < current_time:
      data['past_shows'].append({
        'venue_id': show.venue_id,
        'venue_name': show.name,
        'venue_image_link': show.image_link,
        'start_time': format_datetime(str(show.start_time))
      })
      data['past_shows_count'] = data['past_shows_count'] + 1
    else:
      data['upcoming_shows'].append({
        'venue_id': show.venue_id,
        'venue_name': show.name,
        'venue_image_link': show.image_link,
        'start_time': format_datetime(str(show.start_time))
      })
      data['upcoming_shows_count'] = data['upcoming_shows_count'] + 1 

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------

# Route handler for artist edit form Get
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm(request.form)
  artist = db.session.query(Artist).filter(Artist.id == artist_id).first()

  #set active placeholders
  form.name.process_data(artist.name)
  form.city.process_data(artist.city)
  form.state.process_data(artist.state)
  form.phone.process_data(artist.phone)

  # tip: https://stackoverflow.com/questions/5519729/wtforms-how-to-select-options-in-selectmultiplefield

  # For SelectMultipleField we need data as a list
  # in database its saved as a string 
  # and is separated by comma and has open/close beaces
  genres = artist.genres.replace("{", "")
  genres = genres.replace("}", "")
  genres = genres.split(",")
  form.genres.process_data(genres)
  form.image_link.process_data(artist.image_link)
  form.facebook_link.process_data(artist.facebook_link)
  form.website.process_data(artist.website)
  # seeking venue is saved in database as True/False
  # One form its represented as Yes/No
  if (artist.seeking_venue == True):
    form.seeking_venue.process_data("Yes")
  else:
    form.seeking_venue.process_data("No")

  form.seeking_description.process_data(artist.seeking_description) 

  return render_template('forms/edit_artist.html', form=form, artist=artist)

# Edit artist POST handler
@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    form = ArtistForm()
    artist = db.session.query(Artist).filter(Artist.id == artist_id).first()
    # updating values from form input
    artist.name = form.name.data
    artist.city = form.city.data
    artist.state = form.state.data
    artist.phone = form.phone.data
    artist.genres = form.genres.data
    artist.image_link = form.image_link.data
    artist.facebook_link = form.facebook_link.data
    artist.website = form.website.data
    if form.seeking_venue.data == 'Yes':
      artist.seeking_venue = True
    else:
      artist.seeking_venue = False
    artist.seeking_description = form.seeking_description.data
    db.session.commit()
    # on successful db insert, flash success
    flash('Artist ' + request.form['name'] + ' was successfully updated!')
  except:
    print(sys.exc_info())
    db.session.rollback()
    # on successful db insert, flash success
    flash('An error occured. Artist ' + request.form['name'] + ' could not be updated.')
  finally:
    db.session.close()
  # return back to artist page
  return redirect(url_for('show_artist', artist_id=artist_id))

# Route handler for Venue edit form GET
@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm(request.form)
    
  venue = db.session.query(Venue).filter(Venue.id == venue_id).first()

  #set active placeholders
  form.name.process_data(venue.name)
  # tip: https://stackoverflow.com/questions/5519729/wtforms-how-to-select-options-in-selectmultiplefield

  # For SelectMultipleField we need data as a list
  # In database venue.genres is already a list 
  form.genres.process_data(venue.genres)
  form.address.process_data(venue.address)
  form.city.process_data(venue.city)
  form.state.process_data(venue.state)
  form.phone.process_data(venue.phone)
  form.website.process_data(venue.website)
  form.facebook_link.process_data(venue.facebook_link)
    
  # seeking venue is saved in database as True/False
  # One form its represented as Yes/No
  if (venue.seeking_talent == True):
    form.seeking_talent.process_data("Yes")
  else:
    form.seeking_talent.process_data("No")

  form.seeking_description.process_data(venue.seeking_description)
  form.image_link.process_data(venue.image_link) 
  
  return render_template('forms/edit_venue.html', form=form, venue=venue)

# Venue edit POST handler
@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  
  try:
    form = VenueForm()
    venue = db.session.query(Venue).filter(Venue.id == venue_id).first()
    # updating values from form input
    venue.name = form.name.data
    venue.genres = form.genres.data
    venue.address = form.address.data
    venue.city = form.city.data
    venue.state = form.state.data
    venue.phone = form.phone.data
    venue.website = form.website.data
    venue.facebook_link = form.facebook_link.data 
    
    if form.seeking_talent.data == 'Yes':
      venue.seeking_talent = True
    else:
      venue.seeking_talent = False
    venue.seeking_description = form.seeking_description.data
    venue.image_link = form.image_link.data
    db.session.commit()
    # on successful db insert, flash success
    flash('Venue ' + request.form['name'] + ' was successfully updated!')
  except:
    print(sys.exc_info())
    db.session.rollback()
    # on successful db insert, flash success
    flash('An error occured. Venue ' + request.form['name'] + ' could not be updated.')
  finally:
    db.session.close()
  # return back to venue page
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

# Artist creation GET route handler
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

# Artist Creation POST handler
@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  
  try:
    form = ArtistForm()
    name = form.name.data
    city = form.city.data
    state = form.state.data
    phone = form.phone.data
    genres = form.genres.data
    facebook_link = form.facebook_link.data
    website = form.website.data
    image_link = form.image_link.data
    if form.seeking_venue.data == 'Yes':
      seeking_venue = True
    else:
      seeking_venue = False
    seeking_description = form.seeking_description.data

    artist = Artist(name=name, city=city,state=state,
        phone=phone, genres=genres, 
        facebook_link=facebook_link, website=website,
        image_link=image_link, seeking_venue = seeking_venue,
        seeking_description = seeking_description
        )
    db.session.add(artist)
    db.session.commit()
    # on successful db insert, flash success
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occured. Artist ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

# Route handler for shows page
@app.route('/shows')
def shows():
  
  shows = db.session.query(Show).all()
  data = []
  for show in shows:
    show_data = {
      "venue_id": show.venue_id,
      "venue_name": db.session.query(Venue.name).filter(Venue.id == show.venue_id).first()[0],
      "artist_id": show.artist_id,
      "artist_name": db.session.query(Artist.name).filter(Artist.id == show.artist_id).first()[0],
      "artist_image_link": db.session.query(Artist.image_link).filter(Artist.id == show.artist_id).first()[0],
      "start_time": format_datetime(str(show.start_time))
    }
    data.append(show_data)
   
  return render_template('pages/shows.html', shows=data)

# Route handler for rendering Create Shows page
@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    form = ShowForm()
    venue_id = form.venue_id.data
    artist_id = form.artist_id.data
    start_time = form.start_time.data

    show = Show(venue_id=venue_id, 
        artist_id=artist_id, 
        start_time=start_time
        )
    db.session.add(show)
    db.session.commit()
    # on successful db insert, flash success
    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occured. Show could not be listed.')
  finally:
    db.session.close()

  return render_template('pages/home.html')

# error handlers

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
