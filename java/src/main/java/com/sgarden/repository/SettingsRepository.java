package com.sgarden.repository;

import com.sgarden.model.AppSetting;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface SettingsRepository extends MongoRepository<AppSetting, String> {
    Optional<AppSetting> findByKey(String key);
}
