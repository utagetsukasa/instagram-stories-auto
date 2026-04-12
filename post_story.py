  import os                                                         
  import requests                                                   
  import jpholiday                                                  
  from datetime import date                                 
                                                                    
  def get_today_image():                                    
      today = date.today()
      if jpholiday.is_holiday(today):
          return "holiday.png"
      day_map = {                             
          0: "monday.png",                
          1: "tuesday.png",
          2: "wednesday.png",                                       
          3: "thursday.png",
          4: "friday.png",                                          
          5: "saturday.png",                                
          6: "sunday.png",                    
      }                                   
      return day_map[today.weekday()]
                                                                    
  def post_story(image_filename):
      user_id = os.environ["INSTAGRAM_USER_ID"]                     
      access_token = os.environ["INSTAGRAM_ACCESS_TOKEN"]   
      repo = os.environ["GITHUB_REPOSITORY"]  
      image_url =                         
  f"https://raw.githubusercontent.com/{repo}/main/{image_filename}"
                                                                    
      create_url =                            
  f"https://graph.instagram.com/v21.0/{user_id}/media"              
      create_params = {                                     
          "image_url": image_url,                                   
          "media_type": "STORIES",
          "access_token": access_token,                             
      }                                                     
      response = requests.post(create_url, params=create_params)
      response.raise_for_status()             
      creation_id = response.json()["id"] 

      publish_url =                                                 
  f"https://graph.instagram.com/v21.0/{user_id}/media_publish"
      publish_params = {                                            
          "creation_id": creation_id,                               
          "access_token": access_token,
      }                                                             
      response = requests.post(publish_url, params=publish_params)
      response.raise_for_status()
      print(f"投稿完了: {image_filename}")    
                                          
  if __name__ == "__main__":
      image = get_today_image()                                     
      print(f"本日の画像: {image}")
      post_story(image)                                             
