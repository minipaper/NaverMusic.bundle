# -*- coding: utf-8 -*-

import urllib, unicodedata, json, difflib

BASE_URL = 'http://music.naver.com'

ARTIST_SEARCH_URL = BASE_URL + '/search/search.nhn?query=%s&target=artist'
ARTIST_INFO_URL = BASE_URL + '/artist/intro.nhn?artistId=%s'
#ARTIST_ALBUM_URL = BASE_URL + '/artist/album.nhn?artistId=%s&isRegular=Y&sorting=popular'

ARTIST_ALBUM_URL = BASE_URL + '/artist/album.nhn?artistId=%s'
ARTIST_ALBUM_URL2 = BASE_URL + '/artist/album.nhn?artistId=%s&page=2'
ARTIST_PHOTO_URL = BASE_URL + '/artist/photo.nhn?artistId=%s'

ALBUM_SEARCH_URL = BASE_URL + '/search/search.nhn?query=%s&target=album'
ALBUM_INFO_URL = BASE_URL + '/album/index.nhn?albumId=%s'

VARIOUS_ARTISTS_POSTER = 'http://userserve-ak.last.fm/serve/252/46209667.png'

RE_ARTIST_ID = Regex('artistId=(\d+)')
RE_ALBUM_ID = Regex('albumId=(\d+)')
RE_ALBUM_RATING = Regex(u'평점'+' (.*?)'+u'점')

def Start():
  HTTP.CacheTime = CACHE_1WEEK

########################################################################  
class NaverMusicAgent(Agent.Artist):
  name = 'Naver Music'
  languages = [Locale.Language.Korean, Locale.Language.English]
  accepts_from = ['com.plexapp.agents.localmedia']

  def search(self, results, media, lang, manual):

    # Handle a couple of edge cases where artist search will give bad results.
    if media.artist == '[Unknown Artist]': 
      return
    if media.artist == 'Various Artists':
      results.Append(MetadataSearchResult(id = 'Various%20Artists', name= 'Various Artists', thumb = VARIOUS_ARTISTS_POSTER, lang  = lang, score = 100))
      return
    
    # Search for artist.
    Log('Artist search: ' + media.artist)
    if manual:
      Log('Running custom search...')
      # Added 2016.3.25
      media_name = unicodedata.normalize('NFKC', unicode(media.artist)).strip()
    else:
      media_name = media.artist

    #artists = self.score_artists(media, lang, SearchArtists(media.artist))
    artists = self.score_artists(media, lang, SearchArtists(media_name))
    Log('Found ' + str(len(artists)) + ' artists...')

    for artist in artists:
      results.Append( MetadataSearchResult(id=artist['id'], name=artist['name'], lang=artist['lang'], score=artist['score']) )















  def score_artists(self, media, lang, artists):
    for i, artist in enumerate(artists):
      id = artist['id']
      name = artist['name']

      #score = 80 if i == 0 else 50
      
      Log.Debug('Score...' + name.lower() + ' - ' + media.artist.lower())
      #Log.Debug('Score2...' + name.strip().lower().decode('utf-8') + ' - ' + media.artist.strip().lower().decode('utf-8'))
      #s = difflib.SequenceMatcher(None, name.strip().lower().encode('utf-8'), media.artist.strip().lower())
      s = difflib.SequenceMatcher(None, unicodedata.normalize('NFKC', unicode(name.lower())).strip(), unicodedata.normalize('NFKC', unicode(media.artist.lower())).strip())
      score = int(s.ratio() * 100)

      artists[i]['score'] = score
      artists[i]['lang'] = lang
      Log.Debug('id: %s name: %s score: %d lang: %s' % (id, name, score, lang))
    return artists







  def update(self, metadata, media, lang):
    url = ARTIST_INFO_URL % metadata.id
    try: 
      html = HTML.ElementFromURL(url)
    except:
      raise Ex.MediaExpired

    #metadata.title = html.xpath('//span[@class="txt"]')[0].text
    #metadata.title = html.xpath('//meta[@property="og:title"]')['content']
    #metadata.title = html.xpath('//meta[@property="og:title"]')[0].get("content")
    tmp = html.xpath('//meta[@property="og:title"]')[0].get("content")
    metadata.title = tmp.split('::')[1].strip() if tmp.find('::') != -1 else tmp
    Log.Debug('Artist Title: ' + metadata.title)
    
    #metadata.year = html.xpath('//dt[@class="birth"]/following-sibling::dd')[0].text
    
    try:
      #metadata.summary = String.DecodeHTMLEntities(String.StripTags(html.xpath('//p[@class="dsc full"]')[0].text).strip())
      #metadata.summary = html.xpath('//p[@class="dsc full"]')[0].text.sub('<[^<]+?>', '', text)
      #metadata.summary = '\n'.join(html.xpath('//p[@class="dsc full"]//text()'))
      #metadata.summary = '\n'.join(html.xpath('//div[@class="mscn_info_lst"]//text()'))
      
      summary = ''
      common = html.xpath('//div[@class="common"]//dt/text()')
      common2 = html.xpath('//div[@class="common"]//dd/text()')
      for i in range(0, len(common)):
        summary += common[i].strip() + ' : ' 
        xpath_str = '//div[@class="common"]//dd[%d]/a/text()' % (i+1)
        temp = html.xpath(xpath_str)
        if 0 == len(temp): summary += common2[i].strip()
        else: summary += ','.join(temp)
        summary += '\n'
      summary += '\n'
      summary += '\n'.join(html.xpath('//p[@class="dsc full"]//text()'))
      summary.strip()
      metadata.summary = summary

    except:
      pass

    # poster
    if metadata.title == 'Various Artists':
      metadata.posters[VARIOUS_ARTISTS_POSTER] = Proxy.Media(HTTP.Request(VARIOUS_ARTISTS_POSTER))
    else:
      #img_url = html.xpath('//div[@class="info"]/div[contains(@class, "thumb")]/img')[0].get('src')
      img_url = html.xpath('//span[@class="thmb"]/span[contains(@class, "crop")]/img')[0].get('src')
      metadata.posters[img_url] = Proxy.Media(HTTP.Request(img_url))

    # genre
    metadata.genres.clear()
    try:
      #for genre in html.xpath("//dt[text()='스타일']/following-sibling::dd")[0].text.split(','):
      #for genre in html.xpath('//dt[@class="v1"]/following-sibling::dd')[0].text.split(','):
      for genre in html.xpath('//strong[@class="genre"]')[0].text.split(','):
        metadata.genres.add(genre.strip())
    except:
      pass

    # similar artist
    metadata.similar.clear()
    try:
      #for genre in html.xpath("//dt[text()='스타일']/following-sibling::dd")[0].text.split(','):
      #for genre in html.xpath('//dt[@class="v1"]/following-sibling::dd')[0].text.split(','):
      for similar in html.xpath('//strong[@class="tit"]'):
        metadata.similar.add(similar.text.strip())
        #Log.Debug('Similar Add.. '+similar.text.strip())
    except:
      pass

    # artwork
    #if Prefs['artwork']:
    #  url = ARTIST_PHOTO_URL % metadata.id
    #  try: 
    #    html = HTML.ElementFromURL(url)
    #  except:
    #    raise Ex.MediaExpired

    #  for i, node in enumerate(html.xpath('//ul[contains(@class, "lst_photo")]//img')):
    #    thumb = node.get('src')
    #    img_url = thumb.replace('/thumbnail/', '/body/')
    #    metadata.art[img_url] = Proxy.Preview(HTTP.Request(thumb), sort_order=(i+1))
    
    params = urllib.urlencode({'page': 1, 'artistId': metadata.id, 'musicianId': -1})
    r = urllib.urlopen("http://music.naver.com/artist/photoListJson.nhn", params).read()
    r = r.replace('thumbnail', '"thumbnail"')
    r = r.replace('original', '"original"')
    data = json.loads(r)
    jdata = data["photoList"]
    for i, item in enumerate(jdata):
      thumb = item.get("original")
      metadata.art[thumb] = Proxy.Preview(HTTP.Request(thumb), sort_order=(i+1))
      if i > 3:
        break

########################################################################  
class NaverMusicAlbumAgent(Agent.Album):
  name = 'Naver Music'
  languages = [Locale.Language.Korean, Locale.Language.English]
  accepts_from = ['com.plexapp.agents.localmedia']

  def search(self, results, media, lang, manual):    
    if media.parent_metadata.id is None:
      return

    # Search for album.
    if manual:
      Log('Running custom search...')
      # Added 2016.3.25
      media_name = unicodedata.normalize('NFKC', unicode(media.name)).strip()
    else:
      media_name = media.title
    Log('Album search: ' + media_name)

    #albums = self.score_albums(media, lang, SearchAlbums(media.artist, media.title))
    #albums = self.score_albums(media, lang, SearchAlbums(unicode(media.parent_metadata.title), media.title))
    albums = self.score_albums(media, lang, SearchAlbums(unicode(media.parent_metadata.title), media_name))
    Log('Found ' + str(len(albums)) + ' albums...')

    for album in albums:
      results.Append( MetadataSearchResult(id=album['id'], name=album['name'], lang=album['lang'], score=album['score']) )

    if len(albums) > 0:
      return

    Log('2nd try...')
    albums = self.score_albums(media, lang, GetAlbumsByArtist(media.parent_metadata.id), legacy=True)
    Log('Found ' + str(len(albums)) + ' albums...')

    for album in albums:
      results.Append( MetadataSearchResult(id=album['id'], name=album['name'], lang=album['lang'], score=album['score']) )

  def score_albums(self, media, lang, albums, legacy=False):

    for i, album in enumerate(albums):
      id = album['id']
      name = album['name']

      #if legacy:
      #  score = 80 if name in media.title else 50
      #else:
      #  score = 80 if i == 0 else 50
        
      s = difflib.SequenceMatcher(None, name.lower(), media.title.lower())
      score = int(s.ratio() * 100)      

      albums[i]['score'] = score
      albums[i]['lang'] = lang
      Log.Debug('id: %s name: %s score: %d lang: %s' % (id, name, score, lang))
    return albums

  def update(self, metadata, media, lang):
    Log.Debug('query album: '+metadata.id)
    url = ALBUM_INFO_URL % metadata.id
    try: 
      html = HTML.ElementFromURL(url)
    except:
      raise Ex.MediaExpired

    metadata.title = html.xpath('//h2')[0].text
    #metadata.album = html.xpath('//h2')[0].text
    #metadata.name = html.xpath('//h2')[0].text
    Log('Album Title: ' + html.xpath('//h2')[0].text)

    date_s = html.xpath('//dt[@class="date"]/following-sibling::dd')[0].text
    date_s = date_s.replace(".", "-")
    try:
      metadata.originally_available_at = Datetime.ParseDate(date_s)
    except:
      pass
      
    # rating
    try:
      metadata.rating = float(RE_ALBUM_RATING.search(html.xpath('//span[@class="_album_rating"]/em')[0].text).group(1))
    except:
      pass    
      
    #Log('Rating: ' + str(metadata.rating))

    try:
      #metadata.summary = String.DecodeHTMLEntities(String.StripTags(html.xpath('//p[contains(@class, "intro_desc")]')[0].text).strip())
      #metadata.summary = '\n'.join(String.StripTags(html.xpath('//p[contains(@class, "intro_desc")]//text()')))
      #metadata.summary = '\n'.join(String.StripTags(html.xpath('//p[contains(@class, "intro_desc")]//text()')))

      common = html.xpath('//dl[@class="desc"]//dt/span/text()')
      common2 = html.xpath('//dl[@class="desc"]//dd/text()')
      intro = html.xpath('//p[contains(@class, "intro_desc")]//text()')
      summary = ''
      metadata.summary = '1111'
      for i in range(0, len(common)):
        metadata.summary = summary
        summary += common[i].strip() + ' : ' 
        metadata.summary = summary
        xpath_str = '//dl[@class="desc"]//dd[%d]/a/text()' % (i+1)
        temp = html.xpath(xpath_str)
        if 0 == len(temp): summary += common2[i+1].strip()
        else: summary += ','.join(temp)
        metadata.summary = summary
        summary += '\n'
      
      summary += '\n'
      for str in intro:
        summary += str.strip() + '\n'
      summary.strip()
      metadata.summary = summary
      
      metadata.studio = common2[4].strip()

    except:
      #metadata.summary = 'aaaaaaaaaaa'
      pass

    # poster
    img_url = html.xpath('//meta[@property="og:image"]')[0].get('content')
    metadata.posters[img_url] = Proxy.Media(HTTP.Request(img_url))

    # genre
    metadata.genres.clear()
    
    # No genre case exist
    try:
      for genre in html.xpath('//dt[@class="type"]/following-sibling::dd')[0].text.split(','):
        metadata.genres.add(genre.strip())
    except:
      pass

########################################################################  
def SearchArtists(artist):
  url = ARTIST_SEARCH_URL % String.Quote(artist.encode('utf-8'))
  try: 
    html = HTML.ElementFromURL(url)
  except:
    raise Ex.MediaExpired

  artists = []
  #for node in html.xpath('//dt/a'):
  for node in html.xpath('//li[@style="width:49.9%"]'):
    try:
      id = RE_ARTIST_ID.search(node.xpath('./dl/dt/a')[0].get('href')).group(1)
      # 곡을 찾는데 앨범수가 나온다
      n_album = node.xpath('./dl/dd/a/em')[0].text
      artists.append({'id':id, 'name':node.xpath('./dl/dt/a')[0].get('title') })
    except:
      pass
  return artists

def SearchAlbums(artist, album):
  if artist in album:
    q_str = album
  elif artist == 'None':
    q_str = album  
  else:
    q_str = album+' '+artist

  url = ALBUM_SEARCH_URL % String.Quote(q_str.encode('utf-8'))
  try: 
    html = HTML.ElementFromURL(url)
  except:
    raise Ex.MediaExpired

  album = []
  for node in html.xpath('//dt/a'):
    id = RE_ALBUM_ID.search(node.get('href')).group(1)
    album.append({'id':id, 'name':node.get('title')})
  return album

def GetAlbumsByArtist(artist, albums=[]):
  url = ARTIST_ALBUM_URL % artist
  try: 
    html = HTML.ElementFromURL(url)
  except:
    raise Ex.MediaExpired

  album = []
  #for node in html.xpath('//a[contains(@class, "NPI=a:name")]'):
  for node in html.xpath('//div[@class="thmb_cover"]'):
    id = RE_ALBUM_ID.search(node.xpath('a')[0].get('href')).group(1)
    album.append({'id':id, 'name':node.xpath('./a/p/strong')[0].text})

  url = ARTIST_ALBUM_URL2 % artist
  try: 
    html = HTML.ElementFromURL(url)
  except:
    raise Ex.MediaExpired

  #for node in html.xpath('//a[contains(@class, "NPI=a:name")]'):
  for node in html.xpath('//div[@class="thmb_cover"]'):
    id = RE_ALBUM_ID.search(node.xpath('a')[0].get('href')).group(1)
    album.append({'id':id, 'name':node.xpath('./a/p/strong')[0].text})

  return album
