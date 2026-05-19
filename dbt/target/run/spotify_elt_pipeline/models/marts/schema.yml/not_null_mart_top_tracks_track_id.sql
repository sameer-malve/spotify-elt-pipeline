
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select track_id
from SPOTIFY_DB.STAGING.mart_top_tracks
where track_id is null



  
  
      
    ) dbt_internal_test